"""
Spanish-specific normalization rules.
"""

import html
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
    "despues",
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
    "seleccion",
    "premium",
    "especial",
    "fresco",
    "natural",
    "grande",
    "mediano",
    "pequeno",
    "mini",
    "maxi",
    "envase",
    "paquete",
    "pack",
    "caja",
    "box",
    "unidad",
    "unidades",
    "u",
    "ud",
    "uds",
    "cada uno",
    "pieza",
    "piezas",
    "botella",
    "lata",
    "tetrabrik",
    "deshuesado",
    "racion",
    "raciones",
    "suelto",
    "suelta",
    "sueltos",
    "sueltas",
    "talla",
    "tallas",
    "malla",
    "bandeja",
    "manojo",
    "bote",
    "frasco",
    "tarro",
    "tarrina",
    "autoservicio",
    "autoservici",
    "yo",
    "sabor",
    "variedad",
    "var",
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
    "autentico",
    "genuino",
    "original",
    "clasico",
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
    "frio",
    "templado",
    "rapido",
    "facil",
    "simple",
    "practico",
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
    "auto",
    "automatico",
    # brands
    "el corte ingles",
    "kirkland signature",
}

# Common Spanish food/product abbreviations
EXPANSIONS = {
    "k": "kilo",
    "kg": "kilogramo",
    "gr": "gramo",
    "ml": "mililitro",
    "lt": "litro",
    "pz": "pieza",
    "pza": "pieza",
    "pzas": "piezas",
    "paq": "paquete",
    "bot": "botella",
    "org": "organico",
    "nat": "natural",
    "desc": "descremado",
    "light": "ligero",
    "diet": "dietetico",
    "p": "peso",
    "g": "gramo",
    "l": "litro",
    "und": "unidad",
    "uds": "unidades",
    "env": "envase",
    "ud": "unidad",
    "pk": "paquete",
    "sel": "seleccion",
    "prem": "premium",
    "esp": "especial",
    "eco": "ecologico",
    "bio": "biologico",
    "s/n": "sin",
    "c/": "con",
    "c/u": "cada uno",
    "s/l": "sin lactosa",
    "s/g": "sin gluten",
    "s/a": "sin azucar",
    "s/s": "sin sal",
    "s/h": "deshuesado",
    "c/h": "con hueso",
    "s/p": "sin piel",
    "c/p": "con piel",
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
    "pe": "pequeno",
    "pq": "pequeno",
    "md": "mediano",
    "m": "mediano",
    # already mapped to "grande"
    # "gr": "grande",
    # "g": "grande",
    "ex": "extra",
    "e": "extra",
    # brands
    "eci": "el corte ingles",
    "ks": "kirkland signature",
    # receipt abbreviations and POS truncations
    "choco": "chocolate",
    "chocola": "chocolate",
    "carame": "caramelo",
    "gall": "galleta",
    "marga": "margarina",
    "mante": "mantequilla",
    "pist": "pistacho",
    "trocea": "troceado",
    "ecol": "ecologico",
    "ita": "italiano",
    "verd": "verde",
    "pimien": "pimiento",
    "ban": "bandeja",
    "ba": "bandeja",
    "bd": "bandeja",
    "bo": "bolsa",
    "fc": "frasco",
    "cer": "cerdo",
    "anoj": "anojo",
    "cald": "caldo",
    "servi": "servilletas",
    "servil": "servilletas",
    "ib": "iberico",
    "ext": "extra",
    "mant": "mantequilla",
    "gour": "gourmet",
    "ah": "ahumada",
    "semil": "semilla",
    "varie": "variedad",
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

    # Strip accents from tokens (e.g. "él" -> "el")
    tokens = [
        "".join(
            char
            for char in unicodedata.normalize("NFD", token)
            if unicodedata.category(char) != "Mn"
        )
        for token in tokens
    ]

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

    # Expand abbreviations (splitting multi-word expansions into individual tokens)
    expanded_tokens: list[str] = []
    for token in tokens:
        if token in expansions:
            expanded_tokens.extend(expansions[token].split())
        else:
            expanded_tokens.append(token)
    tokens = expanded_tokens

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
        text = html.unescape(text)
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")

        # Clean leading/trailing punctuation that interferes with spaCy tokenization
        text = re.sub(r"^[^\w\s]+|[^\w\s]+$", "", text).strip()

        # Pre-expand abbreviations containing slashes or dots that spaCy would split into punctuation
        active_expansions = (
            self.custom_expansions if self.custom_expansions is not None else EXPANSIONS
        )
        for pattern, replacement in active_expansions.items():
            if "/" in pattern:
                text = re.sub(
                    rf"(?i)(?<!\w){re.escape(pattern)}(?!\w)", replacement, text
                )

        # Expand "sin hueso" to "deshuesado" (which is a standard cut stopword)
        text = re.sub(r"(?i)\bsin\s+hueso\b", "deshuesado", text)

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
