"""Refactored ProductMatcher using modular strategy-based architecture."""

from typing import Any

from app.models import BackendConfig

from ...models import DebugStep
from ..debug import DebugStepTracker
from .data_preparation import DataPreparation
from .pipeline import MatchingPipeline


class ProductMatcher:
    """Main product matching service using modular strategy-based architecture."""

    def __init__(self) -> None:
        self.data_preparation = DataPreparation()
        self.pipeline = MatchingPipeline()

    def _get_normalizer(self, language: str) -> Any:
        """Get normalizer instance for the requested language from registry.

        Args:
            language: Language code (e.g., 'es')

        Returns:
            Configured normalizer instance

        Raises:
            ValueError: If language not supported
        """
        from app.services.normalization.registry import get_normalizer

        return get_normalizer(language)

    def match_product(
        self,
        input_query: str,
        backend_config: BackendConfig,
        threshold: float = 0.8,
        max_candidates: int = 10,
        debug: DebugStepTracker | None = None,
    ) -> tuple[bool, str, list[tuple[str, float]], list[DebugStep]]:
        """
        Match a product using the modular strategy-based pipeline.

        Args:
            input_query: The user's product query
            backend_config: Backend configuration (contains language and adapter info)
            threshold: Minimum score threshold for fuzzy matching (final fallback)
            max_candidates: Maximum number of candidates to return
            debug: Debug tracker (created if not provided)

        Returns:
            Tuple of (success, normalized_input, matches, debug_info)
            - success: Whether a confident match was found
            - normalized_input: The normalized input query
            - matches: List of (product_id, score) tuples
            - debug_info: Debug information as list of DebugStep objects
        """
        if debug is None:
            debug = DebugStepTracker()

        debug.add(
            f"ProductMatcher.match_product called with: '{input_query}' (language: {backend_config.language}, threshold: {threshold})"
        )

        try:
            # Step 1: Get normalizer for the requested language from registry
            normalizer = self._get_normalizer(backend_config.language)

            # Step 2: Prepare data and context with normalizer
            context = self.data_preparation.prepare_context(
                normalizer, input_query, backend_config, debug
            )

            # Step 2: Execute matching pipeline using user-provided threshold for all strategies
            success, result = self.pipeline.execute(
                context=context,
                semantic_threshold=threshold,  # Use user-provided threshold
                fuzzy_threshold=threshold,  # Use user-provided threshold
                max_candidates=max_candidates,
            )

            # Step 3: Return results in original format
            debug.add(
                f"Pipeline execution completed: success={success}, strategy={result.strategy_name}, matches={len(result.matches)}"
            )

            return (
                success,
                context.normalized_input,
                result.matches,
                debug.get_debug_info(),
            )

        except Exception as e:
            debug.add(f"Error in match_product: {str(e)}")
            return False, input_query, [], debug.get_debug_info()

    def add_learned_alias(
        self, external_product_id: str, alias: str, backend: str
    ) -> tuple[bool, str | None]:
        """
        Add a learned alias to the external system.

        Args:
            external_product_id: ID of the product in external system
            alias: New alias to add

        Returns:
            Tuple of (success boolean, error message if any)
        """
        # This functionality remains unchanged from the original implementation
        # Import here to avoid circular imports
        from ...adapters.registry import get_backend

        try:
            # Note: We don't have backend info here, so this would need to be
            # passed in or stored as instance variable if needed
            # For now, keeping the same signature but noting the limitation
            backend_adapter = get_backend(backend)

            if hasattr(backend_adapter, "add_alias"):
                success = backend_adapter.add_alias(external_product_id, alias)
                if success:
                    return True, None
                else:
                    return False, "Backend failed to add alias"
            else:
                return False, "Backend does not support adding aliases"

        except Exception as e:
            return False, f"Error adding learned alias: {str(e)}"
