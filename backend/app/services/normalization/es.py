"""
Spanish-specific normalization rules.
"""

from typing import Any

import spacy

# Common Spanish stopwords to remove
STOPWORDS = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "y",
    "o",
    "pero",
    "en",
    "con",
    "por",
    "para",
    "de",
    "del",
    "al",
    "desde",
    "hasta",
    "sobre",
    "bajo",
    "entre",
    "durante",
    "antes",
    "después",
    "encima",
    "debajo",
    "es",
    "son",
    "era",
    "eran",
    "ser",
    "sido",
    "siendo",
    "tener",
    "tiene",
    "tenido",
    "hacer",
    "hace",
    "hecho",
    "este",
    "esta",
    "estos",
    "estas",
    "ese",
    "esa",
    "esos",
    "esas",
    "aquel",
    "aquella",
    "aquellos",
    "aquellas",
}

# Common Spanish food/product abbreviations
EXPANSIONS = {
    "kg": "kilogramo",
    "gr": "gramo",
    "ml": "mililitro",
    "lt": "litro",
    "pza": "pieza",
    "pzas": "piezas",
    "paq": "paquete",
    "bot": "botella",
    "lata": "lata",
    "org": "orgánico",
    "nat": "natural",
    "desc": "descremado",
    "sin": "sin",
    "light": "ligero",
    "diet": "dietético",
}


def fast_normalize(text: str) -> str:
    """
    Fast normalization operations (no spaCy):
    - Lowercase
    - Strip accents
    - Remove punctuation
    - Basic cleanup
    """
    import re
    import unicodedata

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


# Global spaCy model - loaded at module import time

try:
    _nlp_model = spacy.load("es_core_news_sm")
except OSError:
    raise RuntimeError(
        "spaCy Spanish model 'es_core_news_sm' not found. "
        "Please ensure the model is installed in the Docker container."
    )


def _get_spacy_model() -> Any:
    """Get the pre-loaded spaCy model."""
    return _nlp_model


def tokenize_text(fast_normalized_text: str) -> Any:
    """
    SpaCy tokenization step:
    - Use cached spaCy model
    - Tokenize text (but don't lemmatize yet)
    """
    nlp = _get_spacy_model()
    doc = nlp(fast_normalized_text)
    return doc


def lemmatize_tokens(doc: Any) -> list[str]:
    """
    SpaCy lemmatization step:
    - Extract lemmatized tokens from spaCy doc
    - Skip punctuation and spaces
    """
    tokens = [
        token.lemma_.lower()
        for token in doc
        if not token.is_punct and not token.is_space and token.text.strip()
    ]
    return tokens


def post_process_tokens(
    tokens: list[str],
    stopwords: set[str] | None = None,
    expansions: dict[str, str] | None = None,
) -> list[str]:
    """
    Fast post-processing operations:
    - Expand abbreviations
    - Remove stopwords
    - Clean empty tokens

    Args:
        tokens: List of tokens to process
        stopwords: Custom stopwords set (defaults to STOPWORDS if None)
        expansions: Custom expansions dict (defaults to EXPANSIONS if None)
    """
    # Use provided config or defaults
    if expansions is None:
        expansions = EXPANSIONS
    if stopwords is None:
        stopwords = STOPWORDS

    # Expand abbreviations
    tokens = [expansions.get(token, token) for token in tokens]

    # Remove stopwords
    tokens = [token for token in tokens if token not in stopwords]

    # Remove empty tokens after processing
    tokens = [token for token in tokens if token]

    return tokens


def normalize(text: str) -> list[str]:
    """
    Complete Spanish normalization pipeline:
    1. Fast normalization (case, accents, punctuation)
    2. SpaCy tokenization
    3. SpaCy lemmatization
    4. Fast post-processing (abbreviations, stopwords)

    Uses cached spaCy model for better performance.
    """
    fast_normalized = fast_normalize(text)
    doc = tokenize_text(fast_normalized)
    lemmatized_tokens = lemmatize_tokens(doc)
    final_tokens = post_process_tokens(lemmatized_tokens)
    return final_tokens


def normalize_with_config(text: str, config: dict[str, Any] | None = None) -> list[str]:
    """
    Complete Spanish normalization pipeline with configurable stopwords and expansions.

    Args:
        text: Input text to normalize
        config: Optional configuration dict with 'stopwords' and 'expansions' keys

    Returns:
        List of normalized tokens
    """
    if not text or not text.strip():
        return []

    # Extract custom stopwords and expansions from config
    custom_stopwords = None
    custom_expansions = None

    if config:
        if "stopwords" in config:
            custom_stopwords = set(config["stopwords"])
        if "expansions" in config:
            custom_expansions = config["expansions"]

    # Run the normalization pipeline
    fast_normalized = fast_normalize(text)
    doc = tokenize_text(fast_normalized)
    lemmatized_tokens = lemmatize_tokens(doc)
    final_tokens = post_process_tokens(
        lemmatized_tokens, custom_stopwords, custom_expansions
    )
    return final_tokens
