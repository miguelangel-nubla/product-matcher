"""Data preparation for matching with immediate cache expiry."""

import time
from typing import Any

from ..debug import DebugStepTracker
from .context import MatchingContext


class DataPreparation:
    """Prepares and normalizes data for matching strategies."""

    def __init__(self) -> None:
        # Cache with immediate expiry (set to 0 seconds as requested)
        self._cache: dict[str, tuple[list[tuple[str, str, list[str]]], float]] = {}
        self._cache_ttl = 0.0  # Immediate expiry

    def prepare_context(
        self,
        input_query: str,
        language: str,
        backend_config: dict[str, Any],
        debug: DebugStepTracker,
    ) -> MatchingContext:
        """
        Prepare matching context with normalized input and aliases.

        Args:
            input_query: Raw input query to match
            language: Language code for normalization
            backend_config: Backend configuration
            debug: Debug tracker

        Returns:
            MatchingContext with normalized data ready for matching
        """
        debug.add(
            f"Starting data preparation for input: '{input_query}' (language: {language})"
        )

        # Get language module for normalization
        try:
            lang_module = __import__(
                f"app.services.normalization.{language}", fromlist=[language]
            )
        except ImportError:
            debug.add(
                f"Language module not found for '{language}', falling back to basic tokenization"
            )
            lang_module = None

        # Normalize input query
        if lang_module and hasattr(lang_module, "normalize"):
            input_tokens = lang_module.normalize(input_query, None)
            normalized_input = " ".join(input_tokens)
        else:
            # Basic fallback normalization
            normalized_input = input_query.lower().strip()
            input_tokens = normalized_input.split()

        debug.add(
            f"Normalized input: '{input_query}' -> '{normalized_input}' -> tokens: {input_tokens}"
        )

        # Get normalized aliases (with immediate cache expiry)
        normalized_aliases = self._get_normalized_aliases(
            language, backend_config, debug
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
            language=language,
            backend_config=backend_config,
            debug=debug,
        )

    def _get_normalized_aliases(
        self, language: str, backend_config: dict[str, Any], debug: DebugStepTracker
    ) -> list[tuple[str, str, list[str]]]:
        """
        Get normalized aliases with immediate cache expiry.

        Returns:
            List of (product_id, original_alias, tokenized_alias) tuples
        """
        cache_key = f"{language}:{id(backend_config)}"

        # Check cache (but with immediate expiry)
        if cache_key in self._cache:
            cached_data, cache_time = self._cache[cache_key]
            if time.time() - cache_time <= self._cache_ttl:
                debug.add(
                    f"Using cached normalized aliases ({len(cached_data)} entries)"
                )
                return cached_data
            else:
                debug.add("Cache expired, re-normalizing aliases")
                del self._cache[cache_key]

        # Get language module
        try:
            lang_module = __import__(
                f"app.services.normalization.{language}", fromlist=[language]
            )
        except ImportError:
            debug.add(
                f"Language module not found for '{language}', using basic normalization"
            )
            lang_module = None

        # Fetch and normalize aliases
        debug.add("Starting backend alias fetch")
        aliases = self._fetch_aliases_from_backend(backend_config)

        debug.add(
            f"Alias fetch completed, normalizing {len(aliases)} aliases for language '{language}'"
        )
        normalized_aliases = []

        for product_id, alias in aliases:
            if lang_module and hasattr(lang_module, "normalize"):
                tokens = lang_module.normalize(alias, None)
            else:
                # Basic fallback normalization
                normalized_alias = alias.lower().strip()
                tokens = normalized_alias.split()

            normalized_aliases.append((product_id, alias, tokens))

        # Cache the result (even though it expires immediately)
        self._cache[cache_key] = (normalized_aliases, time.time())

        debug.add(
            f"Alias normalization completed: processed {len(normalized_aliases)} aliases"
        )
        return normalized_aliases

    def _fetch_aliases_from_backend(
        self, backend_config: dict[str, Any]
    ) -> list[tuple[str, str]]:
        """
        Fetch aliases from the backend system.

        Args:
            backend_config: Backend configuration (should contain backend name)

        Returns:
            List of (product_id, alias) tuples
        """
        # Import here to avoid circular imports
        from ...adapters.registry import get_backend

        # Extract backend name from config
        # Support both old format {"type": "mock"} and new format {"backend_name": "mock"}
        backend_name = backend_config.get("type") or backend_config.get(
            "backend_name", ""
        )
        if not backend_name:
            raise ValueError(
                "Backend configuration must specify 'type' or 'backend_name'"
            )

        backend = get_backend(backend_name)
        products = backend.get_all_products()

        aliases = []
        for product in products:
            # Add all aliases (including primary name)
            if hasattr(product, "aliases") and product.aliases:
                for alias in product.aliases:
                    aliases.append((product.id, alias))

        return aliases

    def clear_cache(self) -> None:
        """Clear the normalization cache."""
        self._cache.clear()
