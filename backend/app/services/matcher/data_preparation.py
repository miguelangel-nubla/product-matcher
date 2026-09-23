"""Data preparation for matching with normalizer injection."""

import re
from typing import Any

from app.adapters.base import ProductDatabaseAdapter
from app.services.backend import Backend

from ..debug import DebugStepTracker
from .context import MatchingContext
from .scoring import barcode_key, extract_barcodes


class DataPreparation:
    """Prepares and normalizes data for matching strategies."""

    def __init__(self) -> None:
        pass

    def prepare_context(
        self,
        normalizer: Any,
        input_query: str,
        backend: Backend,
        debug: DebugStepTracker,
        candidate_product_ids: set[str] | None = None,
    ) -> MatchingContext:
        """
        Prepare matching context with normalized input and aliases.

        Args:
            normalizer: Configured normalizer instance
            input_query: Raw input query to match
            backend: Backend instance with adapter and configuration
            debug: Debug tracker
            candidate_product_ids: When set, only aliases/barcodes for these
                product ids are kept. An empty set yields an empty catalog.

        Returns:
            MatchingContext with normalized data ready for matching
        """
        debug.add(f"Starting data preparation for input: '{input_query}'")

        # Normalize input query using provided normalizer
        input_tokens = normalizer.normalize(input_query)
        normalized_input = (" ".join(input_tokens) or input_query.strip())[:255]

        debug.add(
            f"Normalized input: '{input_query}' -> '{normalized_input}' -> tokens: {input_tokens}"
        )

        # Get normalized aliases - pass normalizer instance. When a shortlist is
        # set, filter raw rows before normalize / barcode index so we do not
        # pay catalog-wide tokenization for a two-id kitchen beep.
        normalized_aliases = self._get_normalized_aliases(
            normalizer,
            debug,
            backend.adapter,
            candidate_product_ids=candidate_product_ids,
        )
        barcodes = self._index_barcodes(
            backend.adapter,
            debug,
            candidate_product_ids=candidate_product_ids,
        )
        if candidate_product_ids is not None:
            debug.add(
                "Constrained candidate filter applied",
                {
                    "candidate_product_ids": sorted(
                        {str(pid) for pid in candidate_product_ids}
                    ),
                    "aliases_after": len(normalized_aliases),
                    "barcode_products_after": len(barcodes),
                },
            )
        query_barcodes = extract_barcodes(input_query)

        # Prepare debug data with input tokens and all aliases
        preparation_data = {
            "input_tokens": input_tokens,
            "normalized_aliases": [
                {
                    "product_id": product_id,
                    "original_alias": original_alias,
                    "normalized_tokens": alias_tokens,
                }
                for product_id, original_alias, alias_tokens in normalized_aliases
            ],
        }

        preparation_data["query_barcodes"] = query_barcodes
        preparation_data["barcodes"] = barcodes
        if candidate_product_ids is not None:
            preparation_data["candidate_product_ids"] = sorted(
                {str(pid) for pid in candidate_product_ids}
            )

        debug.add(
            f"Data preparation completed: {len(input_tokens)} input tokens, {len(normalized_aliases)} normalized aliases, {len(barcodes)} barcodes",
            preparation_data,
        )

        return MatchingContext(
            input_tokens=input_tokens,
            normalized_input=normalized_input,
            normalized_aliases=normalized_aliases,
            backend=backend,
            debug=debug,
            barcodes=barcodes,
            query_barcodes=query_barcodes,
            raw_input=input_query,
        )

    def _get_normalized_aliases(
        self,
        normalizer: Any,
        debug: DebugStepTracker,
        backend_adapter: ProductDatabaseAdapter,
        candidate_product_ids: set[str] | None = None,
    ) -> list[tuple[str, str, list[str]]]:
        """
        Get normalized aliases with immediate cache expiry.

        When ``candidate_product_ids`` is set, only those product ids are
        normalized (empty set → no aliases).

        Returns:
            List of (product_id, original_alias, tokenized_alias) tuples
        """
        # No cache check here - we'll cache individual normalizations below

        # Fetch and normalize aliases
        debug.add("Starting backend alias fetch")
        aliases = backend_adapter.get_all_aliases()
        fetched = len(aliases)
        if candidate_product_ids is not None:
            aliases = [
                (product_id, alias)
                for product_id, alias in aliases
                if str(product_id) in candidate_product_ids
            ]

        debug.add(
            f"Alias fetch completed, normalizing {len(aliases)} aliases"
            + (
                f" (filtered from {fetched})"
                if candidate_product_ids is not None
                else ""
            )
        )
        normalized_aliases = []

        # Use same normalizer instance for all aliases (includes automatic caching)
        for product_id, alias in aliases:
            tokens = normalizer.normalize(alias)
            normalized_aliases.append((product_id, alias, tokens))

        debug.add(
            f"Alias normalization completed: processed {len(normalized_aliases)} aliases"
        )
        return normalized_aliases

    def _index_barcodes(
        self,
        backend_adapter: ProductDatabaseAdapter,
        debug: DebugStepTracker,
        candidate_product_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        """Index catalog barcodes for exact matching.

        A non-list return means products are not available from this adapter
        call. Name matching still runs; barcode keys are simply absent.
        When ``candidate_product_ids`` is set, only those products are indexed.
        """
        products = backend_adapter.get_all_products()
        if not isinstance(products, list):
            debug.add("Barcode index skipped: product list unavailable")
            return {}

        barcodes: dict[str, Any] = {}
        total_barcodes = 0
        for product in products:
            product_id = str(product.id)
            if (
                candidate_product_ids is not None
                and product_id not in candidate_product_ids
            ):
                continue
            keys: list[str] = []

            raw_barcodes = getattr(product, "barcodes", None)
            if raw_barcodes and isinstance(raw_barcodes, list | tuple | set):
                for raw in raw_barcodes:
                    k = barcode_key(str(raw))
                    if len(k) >= 8 and k not in keys:
                        keys.append(k)

            raw_single = getattr(product, "barcode", None)
            if raw_single:
                for piece in re.split(r"[,;\s]+", str(raw_single)):
                    if not piece:
                        continue
                    k = barcode_key(piece)
                    if len(k) >= 8 and k not in keys:
                        keys.append(k)

            if keys:
                barcodes[product_id] = keys[0] if len(keys) == 1 else keys
                total_barcodes += len(keys)

        debug.add(
            f"Indexed {total_barcodes} product barcode(s) across {len(barcodes)} product(s)"
        )
        return barcodes

    def clear_cache(self, normalizer: Any) -> None:
        """Clear the normalization cache in the provided normalizer."""
        normalizer.clear_cache()
