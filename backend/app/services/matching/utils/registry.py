"""Registry for language-specific matching utilities."""

from typing import Any

from .en import EnglishMatchingUtils
from .es import SpanishMatchingUtils


class MatchingUtilsRegistry:
    """Registry for managing language-specific matching utilities."""

    def __init__(self) -> None:
        self._utils: dict[str, Any] = {}

    def register(self, language: str, utils: Any) -> None:
        """Register matching utilities for a language."""
        self._utils[language] = utils

    def get(self, language: str) -> Any:
        """Get matching utilities for a language."""
        if language not in self._utils:
            if language == "en":
                self.register("en", EnglishMatchingUtils())
            elif language == "es":
                self.register("es", SpanishMatchingUtils())
            else:
                raise ValueError(
                    f"No matching utilities registered for language: {language}"
                )
        return self._utils[language]

    def list_languages(self) -> list[str]:
        """Get list of registered languages."""
        return list(self._utils.keys())


# Global registry instance
registry = MatchingUtilsRegistry()


def initialize_matching_utils(language_configs: dict[str, dict[str, Any]]) -> None:
    """Initialize matching utilities for all configured languages.

    Args:
        language_configs: Dictionary mapping language codes to their configurations
    """
    for language, config in language_configs.items():
        if language == "es":
            registry.register(language, SpanishMatchingUtils(config=config))
        elif language == "en":
            registry.register(language, EnglishMatchingUtils(config=config))

    # Ensure defaults exist for supported core languages if not in config
    if "es" not in registry.list_languages():
        registry.register("es", SpanishMatchingUtils())
    if "en" not in registry.list_languages():
        registry.register("en", EnglishMatchingUtils())


def get_matching_utils(language: str) -> Any:
    """Get matching utilities for a language.

    Args:
        language: Language code (e.g., "es", "en")

    Returns:
        Matching utilities instance for the language
    """
    return registry.get(language)
