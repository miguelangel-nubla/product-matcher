"""
Normalization service dispatcher with language-specific modules.
"""

from importlib import import_module
from typing import Any


def normalize_text(
    text: str, lang: str, backend_config: dict[str, Any] | None = None
) -> list[str]:
    """
    Normalize text and return list of normalized tokens.

    Args:
        text: Input text to normalize
        lang: Language code (e.g., 'en', 'es', 'de')
        backend_config: Optional backend configuration containing normalization settings

    Returns:
        List of normalized tokens
    """
    if not text or not text.strip():
        return []

    # Extract normalization config from backend config
    normalization_config = None
    if backend_config and "normalization" in backend_config:
        normalization_config = backend_config["normalization"]

    try:
        module = import_module(f"app.services.normalization.{lang}")
        # Use the unified normalize function that supports optional config
        result = module.normalize(text, normalization_config)
        return result if isinstance(result, list) else []
    except ImportError:
        # Fallback to base normalization
        from app.services.normalization.base import default_normalize_tokens

        return default_normalize_tokens(text)
