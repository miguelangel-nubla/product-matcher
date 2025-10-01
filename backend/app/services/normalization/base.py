"""
Base normalization engine for ProductMatcher.
Provides general text normalization with language-specific extensions.
"""

import re
import unicodedata


def default_normalize(text: str) -> str:
    """
    Default normalization pipeline:
    - Lowercase
    - Remove punctuation and special characters
    - Strip accents
    - Remove extra whitespace
    """
    # Convert to lowercase
    text = text.lower()

    # Strip accents using Unicode normalization
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    # Remove punctuation and special characters, keep only alphanumeric and spaces
    text = re.sub(r"[^\w\s]", " ", text)

    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def default_normalize_tokens(text: str) -> list[str]:
    """
    Default normalization pipeline that returns tokens:
    - Lowercase
    - Strip accents
    - Remove punctuation and special characters
    - Tokenize (split on whitespace)
    - Remove empty tokens
    """
    # Convert to lowercase
    text = text.lower()

    # Strip accents using Unicode normalization
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    # Remove punctuation and special characters, keep only alphanumeric and spaces
    text = re.sub(r"[^\w\s]", " ", text)

    # Tokenize and remove empty tokens
    tokens = [token.strip() for token in text.split() if token.strip()]

    return tokens


def normalize_text(text: str, language: str) -> str:
    """
    Main normalization function that applies general normalization
    and language-specific rules.

    Args:
        text: Input text to normalize
        language: Language code (e.g., 'en', 'es', 'de')

    Returns:
        Normalized text string
    """
    if not text or not text.strip():
        return ""

    # Apply default normalization first
    normalized = default_normalize(text)

    # Apply language-specific normalization if available
    try:
        # Dynamic import of language-specific module
        module = __import__(
            f"app.services.normalization.{language}", fromlist=["normalize"]
        )
        if hasattr(module, "normalize"):
            normalized = module.normalize(normalized)
    except (ImportError, AttributeError):
        # Fallback to default normalization if language module doesn't exist
        pass

    return normalized


def get_available_languages() -> list[str]:
    """
    Get list of supported language codes based on available normalization modules.

    Returns:
        List of language codes (e.g., ['en', 'es'])
    """
    import importlib
    import os

    languages = []
    normalization_dir = os.path.dirname(__file__)

    for filename in os.listdir(normalization_dir):
        if (
            filename.endswith(".py")
            and not filename.startswith("__")
            and filename != "base.py"
        ):
            lang_code = filename[:-3]  # Remove .py extension

            # Verify the module has a normalize function
            try:
                module = importlib.import_module(
                    f"app.services.normalization.{lang_code}"
                )
                if hasattr(module, "normalize") and callable(module.normalize):
                    languages.append(lang_code)
            except ImportError:
                continue

    return sorted(languages)
