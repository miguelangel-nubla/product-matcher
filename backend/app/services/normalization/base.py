"""
Base normalizer class for language-specific text normalization.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseNormalizer(ABC):
    """Abstract base class for text normalizers with instance-level caching."""

    def __init__(self, config: dict[str, Any]):
        """Initialize normalizer with configuration and cache.

        Args:
            config: Optional configuration dict specific to the normalizer
        """
        self.config = config
        self._cache: dict[str, list[str]] = {}

    @abstractmethod
    def _normalize_uncached(self, text: str) -> list[str]:
        """Perform the actual normalization without caching.

        Args:
            text: Input text to normalize

        Returns:
            List of normalized tokens
        """
        pass

    def normalize(self, text: str) -> list[str]:
        """Normalize text with automatic caching.

        Args:
            text: Input text to normalize

        Returns:
            List of normalized tokens
        """
        if not text or not text.strip():
            return []

        # Check cache first
        if text in self._cache:
            return self._cache[text]

        # Perform normalization and cache result
        tokens = self._normalize_uncached(text)
        self._cache[text] = tokens
        return tokens

    def clear_cache(self) -> None:
        """Clear the normalization cache."""
        self._cache.clear()

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics for monitoring.

        Returns:
            Dict with cache size and other stats
        """
        return {"cache_size": len(self._cache), "total_entries": len(self._cache)}
