"""Data preparation for matching with normalizer injection."""

from typing import Any

from app.adapters.base import ProductDatabaseAdapter
from app.services.backend import Backend

from ..debug import DebugStepTracker
from .context import MatchingContext


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
    ) -> MatchingContext:
        """
        Prepare matching context with normalized input and aliases.

        Args:
            normalizer: Configured normalizer instance
            input_query: Raw input query to match
            backend: Backend instance with adapter and configuration
            debug: Debug tracker

        Returns:
            MatchingContext with normalized data ready for matching
        """
        debug.add(f"Starting data preparation for input: '{input_query}'")

        # Normalize input query using provided normalizer
        input_tokens = normalizer.normalize(input_query)
        normalized_input = " ".join(input_tokens)

        debug.add(
            f"Normalized input: '{input_query}' -> '{normalized_input}' -> tokens: {input_tokens}"
        )

        # Get normalized aliases - pass normalizer instance
        normalized_aliases = self._get_normalized_aliases(
            normalizer, debug, backend.adapter
        )

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

        debug.add(
            f"Data preparation completed: {len(input_tokens)} input tokens, {len(normalized_aliases)} normalized aliases",
            preparation_data,
        )

        return MatchingContext(
            input_tokens=input_tokens,
            normalized_input=normalized_input,
            normalized_aliases=normalized_aliases,
            backend=backend,
            debug=debug,
        )

    def _get_normalized_aliases(
        self,
        normalizer: Any,
        debug: DebugStepTracker,
        backend_adapter: ProductDatabaseAdapter,
    ) -> list[tuple[str, str, list[str]]]:
        """
        Get normalized aliases with immediate cache expiry.

        Returns:
            List of (product_id, original_alias, tokenized_alias) tuples
        """
        # No cache check here - we'll cache individual normalizations below

        # Fetch and normalize aliases
        debug.add("Starting backend alias fetch")
        aliases = backend_adapter.get_all_aliases()

        debug.add(f"Alias fetch completed, normalizing {len(aliases)} aliases")
        normalized_aliases = []

        # Use same normalizer instance for all aliases (includes automatic caching)
        for product_id, alias in aliases:
            tokens = normalizer.normalize(alias)
            normalized_aliases.append((product_id, alias, tokens))

        debug.add(
            f"Alias normalization completed: processed {len(normalized_aliases)} aliases"
        )
        return normalized_aliases

    def clear_cache(self, normalizer: Any) -> None:
        """Clear the normalization cache in the provided normalizer."""
        normalizer.clear_cache()
