"""
Spanish-specific normalization rules.
"""

from typing import Any

import spacy
import re

# Common Spanish stopwords to remove
STOPWORDS = {
    "a",
    "b",
    "c",
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
    "extra",
    "peso",
    "granel",
    "baul",
    "kilo",
    "kilogramo",
    "gramo",
    "litro",
    "mililitro",
    "calidad",
    "selección",
    "premium",
    "especial",
    "fresco",
    "natural",
    "grande",
    "mediano",
    "pequeño",
    "mini",
    "maxi",
    "envase",
    "paquete",
    "unidad",
    "pieza",
    "sabor",
    "variedad",
    "marca",
    "tipo",
    "anojo",
    "tradicional",
    "artesanal",
    "casero",
    "hogar",
    "delicioso",
    "sabroso",
    "rico",
    "exquisito",
    "nuevo",
    "mejorado",
    "renovado",
    "actualizado",
    "auténtico",
    "genuino",
    "original",
    "clásico",
    "crujiente",
    "suave",
    "cremoso",
    "tierno",
    "intenso",
    "fuerte",
    "ligero",
    "dulce",
    "salado",
    "picante",
    "amargo",
    "caliente",
    "frío",
    "templado",
    "rápido",
    "fácil",
    "simple",
    "práctico",
    "completo",
    "integral",
    "total",
    "perfecto",
    "selecto",
    "gourmet",
    "chef",
    "profesional",
    "familiar",
    "casa",
    "ªa",
    "ªb",
    "ª",
    "º",
}

# Common Spanish food/product abbreviations
EXPANSIONS = {
    "kg": "kilogramo",
    "gr": "gramo",
    "ml": "mililitro",
    "lt": "litro",
    "pz": "pieza",
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
    "p": "peso",
    "g": "gramo",
    "l": "litro",
    "und": "unidad",
    "uds": "unidades",
    "env": "envase",
    "ud": "unidad",
    "pk": "paquete",
    "sel": "selección",
    "prem": "premium",
    "esp": "especial",
    "eco": "ecológico",
    "bio": "biológico",
    "s/n": "sin",
    "c/": "con",
    "c/u": "cada uno",
    "s/l": "sin lactosa",
    "s/g": "sin gluten",
    "s/a": "sin azúcar",
    "s/s": "sin sal",
    "c/gas": "con gas",
    "s/gas": "sin gas",
    "desr": "desnatado",
    "semidesn": "semidesnatado",
    "ent": "entero",
    "conc": "concentrado",
    "past": "pasteurizado",
    "refr": "refrigerado",
    "cong": "congelado",
    "lat": "lata",
    "tetr": "tetrabrik",
    "brick": "tetrabrik",
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

    # Remove numbers
    text = re.sub(r"\d+", " ", text)

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

    # Strip numbers from tokens
    tokens = [re.sub(r'\d+', '', token) for token in tokens]

    # Expand abbreviations
    tokens = [expansions.get(token, token) for token in tokens]

    # Remove stopwords
    tokens = [token for token in tokens if token not in stopwords]

    # Remove empty tokens after processing
    tokens = [token for token in tokens if token]

    return tokens


def normalize(text: str, config: dict[str, Any] | None) -> list[str]:
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
    import re
    import unicodedata

    # Step 1: Only strip accents, preserve case and punctuation/numbers for spaCy context
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    # Step 2: SpaCy processing with full context (preserve original case for better POS tagging)
    nlp = _get_spacy_model()
    doc = nlp(text)

    # Step 3: Extract lemmatized tokens, filter out punctuation, spaces, and numbers
    tokens = [
        token.lemma_.lower()
        for token in doc
        if not token.is_punct
        and not token.is_space
        and token.text.strip()
        and not token.text.isdigit()
        and not re.match(r'^[\d/]+$', token.text)  # Handle "6/7" style numbers
        and not re.match(r'^[ivxlcdm]+\.?$', token.text.lower())  # Handle Roman numerals like "i.", "ii.", "iii."
    ]

    # Step 4: Post-processing (abbreviations, stopwords) with custom config
    final_tokens = post_process_tokens(tokens, custom_stopwords, custom_expansions)
    return final_tokens
