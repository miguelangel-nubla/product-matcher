"""Backend wrapper that encapsulates both adapter and normalizer."""

from typing import Any

from app.adapters.base import ProductDatabaseAdapter
from app.adapters.registry import get_backend, get_backend_language


class Backend:
    """
    Backend wrapper that provides unified access to both adapter and normalizer.

    Each backend has:
    - adapter: for database operations (get_all_aliases, etc.)
    - normalizer: for language-specific text processing
    """

    def __init__(self, name: str) -> None:
        """
        Create backend instance by name.

        Args:
            name: Backend name from configuration (e.g., "grocy1", "mock")
        """
        self.name = name
        self._adapter = get_backend(name)
        self._language = get_backend_language(name)
        self._normalizer = self._get_normalizer(self._language)

    @property
    def adapter(self) -> ProductDatabaseAdapter:
        """Get the database adapter for this backend."""
        return self._adapter

    @property
    def normalizer(self) -> Any:
        """Get the normalizer for this backend's language."""
        return self._normalizer

    @property
    def language(self) -> str:
        """Get the language code for this backend."""
        return self._language

    def _get_normalizer(self, language: str) -> Any:
        """Get normalizer instance for the backend's language."""
        from app.services.normalization.registry import get_normalizer

        return get_normalizer(language)


def get_backend_instance(backend_name: str) -> Backend:
    """
    Get a complete backend instance with both adapter and normalizer.

    Args:
        backend_name: Backend name from configuration (e.g., "grocy1", "mock")

    Returns:
        Backend instance with adapter and normalizer ready
    """
    return Backend(backend_name)
