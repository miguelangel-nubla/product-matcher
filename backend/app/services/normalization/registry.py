"""Normalizer registry for managing language-specific normalizers."""

from typing import Any

from .base import BaseNormalizer


class NormalizerRegistry:
    """Registry for managing static normalizer instances by language."""

    def __init__(self) -> None:
        self._normalizers: dict[str, BaseNormalizer] = {}

    def register(self, language: str, normalizer: BaseNormalizer) -> None:
        """Register a normalizer for a specific language.

        Args:
            language: Language code (e.g., 'es', 'en')
            normalizer: Configured normalizer instance
        """
        self._normalizers[language] = normalizer

    def get(self, language: str) -> BaseNormalizer:
        """Get normalizer for a language.

        Args:
            language: Language code (e.g., 'es', 'en')

        Returns:
            Normalizer instance

        Raises:
            ValueError: If language not supported
        """
        if language not in self._normalizers:
            raise ValueError(f"No normalizer registered for language: {language}")

        return self._normalizers[language]

    def is_supported(self, language: str) -> bool:
        """Check if a language is supported.

        Args:
            language: Language code to check

        Returns:
            True if language is supported
        """
        return language in self._normalizers

    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages.

        Returns:
            List of language codes
        """
        return list(self._normalizers.keys())

    def clear_cache(self, language: str | None = None) -> None:
        """Clear normalization cache for specific language or all languages.

        Args:
            language: Language to clear cache for, or None for all languages
        """
        if language:
            if language in self._normalizers:
                self._normalizers[language].clear_cache()
        else:
            for normalizer in self._normalizers.values():
                normalizer.clear_cache()


# Global registry instance
registry = NormalizerRegistry()


def initialize_normalizers(language_configs: dict[str, Any]) -> None:
    """Initialize normalizers from language configurations.

    Args:
        language_configs: Dict mapping language codes to normalizer configs
                         e.g., {"es": {"stopwords": [...], "expansions": {...}}}
    """
    for language, config in language_configs.items():
        if language == "es":
            from .es import SpanishNormalizer

            normalizer = SpanishNormalizer(config=config)
            registry.register(language, normalizer)
        else:
            # Hard error for unsupported languages
            raise ValueError(f"No normalizer implementation for language '{language}'")


def get_normalizer(language: str) -> BaseNormalizer:
    """Get normalizer for a language (convenience function).

    Args:
        language: Language code

    Returns:
        Normalizer instance
    """
    return registry.get(language)
