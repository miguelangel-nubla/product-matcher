"""
Spanish-specific normalization rules.
"""

import re
import unicodedata
from typing import Any

import spacy

from .base import BaseNormalizer

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
    "unidades",
    "cada uno",
    "pieza",
    "piezas",
    "botella",
    "lata",
    "tetrabrik",
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
    "normal",
    # brands
    "ks",  # kirkland signature
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
    "nectar": "zumo",
}

# Global spaCy model - loaded at module import time

try:
    _nlp_model = spacy.load("es_core_news_lg")
except OSError:
    raise RuntimeError(
        "spaCy Spanish model 'es_core_news_lg' not found. "
        "Please ensure the model is installed in the Docker container."
    )


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

    # Remove all symbols except alphanumeric
    tokens = [re.sub(r"[^\w]", "", token) for token in tokens]

    # Remove Roman numerals (i, ii, iii, iv, v, vi, vii, viii, ix, x, etc.)
    tokens = [re.sub(r"^[ivx]+$", "", token) for token in tokens]

    # Split numbers and letters into separate tokens (e.g., "75ml" -> "75", "ml")
    split_tokens: list[str] = []
    for token in tokens:
        parts = re.findall(r"\d+|[^\d\s]+", token)
        split_tokens.extend(parts if parts else [token])
    tokens = split_tokens

    # Strip numbers from tokens
    tokens = [re.sub(r"^\d+$", "", token) for token in tokens]

    # Expand abbreviations
    tokens = [expansions.get(token, token) for token in tokens]

    # Remove stopwords
    tokens = [token for token in tokens if token not in stopwords]

    # Remove empty tokens after processing
    tokens = [token for token in tokens if token]

    return tokens


class SpanishNormalizer(BaseNormalizer):
    """Spanish text normalizer with instance-level configuration and caching."""

    def __init__(self, config: dict[str, Any]):
        """Initialize Spanish normalizer with configuration.

        Args:
            config: Configuration dict with 'stopwords' and 'expansions' keys
        """
        super().__init__(config)

        # Extract and store config values for this instance
        self.custom_stopwords = None
        self.custom_expansions = None

        if self.config:
            if "stopwords" in self.config:
                self.custom_stopwords = set(self.config["stopwords"])
            if "expansions" in self.config:
                self.custom_expansions = self.config["expansions"]

    def _normalize_uncached(self, text: str) -> list[str]:
        """Perform Spanish normalization without caching.

        Args:
            text: Input text to normalize

        Returns:
            List of normalized tokens
        """
        # Step 1: Strip accents and clean leading/trailing punctuation
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")

        # Clean leading/trailing punctuation that interferes with spaCy tokenization
        text = re.sub(r"^[^\w\s]+|[^\w\s]+$", "", text).strip()

        # Step 2: SpaCy processing with proper case for better POS tagging
        normalized_case_text = text.title()
        doc = _nlp_model(normalized_case_text)

        # Step 3: Lemmatization (extract lemmas from doc)
        tokens = [
            token.lemma_.lower()
            for token in doc
            if not token.is_punct and not token.is_space
        ]

        # Step 4: Post-processing with instance configuration
        final_tokens = post_process_tokens(
            tokens, self.custom_stopwords, self.custom_expansions
        )
        return final_tokens
