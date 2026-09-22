"""English-specific matching utilities with semantic similarity."""

from collections import OrderedDict
from typing import Any

from .similarity import calculate_semantic_similarity as _calculate


class EnglishMatchingUtils:
    """English language matching utilities with caching."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize English matching utilities.

        Args:
            config: Optional configuration dict
        """
        self.config = config or {}
        self._semantic_cache: OrderedDict[str, float] = OrderedDict()

    def get_doc(self, tokens: list[str]) -> Any:
        """Get spaCy Doc for tokens."""
        text = " ".join(tokens)
        if not text.strip():
            return None
        from ...normalization.en import _nlp_model

        return _nlp_model(text)

    def calculate_semantic_similarity(
        self, tokens1: list[str], tokens2: list[str], doc1: Any | None = None
    ) -> float:
        """Calculate semantic similarity between two token lists with caching.

        Args:
            tokens1: First set of tokens
            tokens2: Second set of tokens
            doc1: Optional precomputed spaCy Doc for tokens1

        Returns:
            Semantic similarity score (0.0 to 1.0)
        """
        from ...normalization.en import _nlp_model

        return _calculate(self._semantic_cache, tokens1, tokens2, _nlp_model, doc1=doc1)

    def clear_cache(self) -> None:
        """Clear the semantic similarity cache."""
        self._semantic_cache.clear()

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics for monitoring.

        Returns:
            Dict with cache size and other stats
        """
        return {
            "semantic_cache_size": len(self._semantic_cache),
            "total_entries": len(self._semantic_cache),
        }
