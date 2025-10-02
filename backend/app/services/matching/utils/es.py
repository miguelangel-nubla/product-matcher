"""Spanish-specific matching utilities with semantic similarity."""

from typing import Any


class SpanishMatchingUtils:
    """Spanish language matching utilities with caching."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize Spanish matching utilities.

        Args:
            config: Optional configuration dict
        """
        self.config = config or {}
        self._semantic_cache: dict[str, float] = {}

    def calculate_semantic_similarity(
        self, tokens1: list[str], tokens2: list[str]
    ) -> float:
        """Calculate semantic similarity between two token lists with caching.

        Args:
            tokens1: First set of tokens
            tokens2: Second set of tokens

        Returns:
            Semantic similarity score (0.0 to 1.0)
        """
        if not tokens1 or not tokens2:
            return 0.0

        # Create cache key from sorted token lists for consistency
        key1 = "|".join(sorted(tokens1))
        key2 = "|".join(sorted(tokens2))
        cache_key = f"{key1}#{key2}"

        # Check cache first
        if cache_key in self._semantic_cache:
            return self._semantic_cache[cache_key]

        # Calculate semantic similarity
        score = self._calculate_semantic_similarity_uncached(tokens1, tokens2)

        # Cache the result
        self._semantic_cache[cache_key] = score
        return score

    def _calculate_semantic_similarity_uncached(
        self, tokens1: list[str], tokens2: list[str]
    ) -> float:
        """Calculate semantic similarity without caching.

        Args:
            tokens1: First set of tokens
            tokens2: Second set of tokens

        Returns:
            Semantic similarity score (0.0 to 1.0)
        """
        text1 = " ".join(tokens1)
        text2 = " ".join(tokens2)

        if not text1.strip() or not text2.strip():
            return 0.0

        # Import spaCy model from normalization module
        from ...normalization.es import _nlp_model

        doc1 = _nlp_model(text1)
        doc2 = _nlp_model(text2)

        # SpaCy's similarity method handles empty vectors gracefully
        return float(doc1.similarity(doc2))

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
