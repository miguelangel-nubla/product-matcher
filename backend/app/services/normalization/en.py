import html
import re
import unicodedata
from typing import Any

import spacy

from .base import BaseNormalizer

# Common English stopwords to remove
STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "up",
    "about",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "among",
    "throughout",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "should",
    "could",
    "can",
    "may",
    "might",
    "must",
    "shall",
    "this",
    "that",
    "these",
    "those",
    "extra",
    "weight",
    "bulk",
    "pound",
    "pounds",
    "ounce",
    "ounces",
    "kilogram",
    "kilograms",
    "gram",
    "grams",
    "milligram",
    "milligrams",
    "liter",
    "liters",
    "milliliter",
    "milliliters",
    "centiliter",
    "centiliters",
    "gallon",
    "gallons",
    "quart",
    "quarts",
    "pint",
    "pints",
    "fluid",
    "quality",
    "selection",
    "premium",
    "special",
    "fresh",
    "natural",
    "large",
    "medium",
    "small",
    "mini",
    "maxi",
    "container",
    "package",
    "packages",
    "unit",
    "units",
    "piece",
    "pieces",
    "pack",
    "packs",
    "flavor",
    "variety",
    "brand",
    "type",
    "traditional",
    "artisanal",
    "homemade",
    "home",
    "delicious",
    "tasty",
    "rich",
    "exquisite",
    "new",
    "improved",
    "renewed",
    "updated",
    "authentic",
    "genuine",
    "original",
    "classic",
    "crispy",
    "soft",
    "creamy",
    "tender",
    "intense",
    "strong",
    "light",
    "sweet",
    "salty",
    "spicy",
    "bitter",
    "hot",
    "cold",
    "warm",
    "quick",
    "easy",
    "simple",
    "practical",
    "complete",
    "whole",
    "total",
    "perfect",
    "select",
    "gourmet",
    "chef",
    "professional",
    "family",
    "house",
}

# Common English food/product abbreviations
EXPANSIONS = {
    "oz": "ounce",
    "ozs": "ounce",
    "lb": "pound",
    "lbs": "pound",
    "kg": "kilogram",
    "g": "gram",
    "gr": "gram",
    "mg": "milligram",
    "l": "liter",
    "lt": "liter",
    "ml": "milliliter",
    "cl": "centiliter",
    "gal": "gallon",
    "qt": "quart",
    "pt": "pint",
    "fl": "fluid",
    "floz": "fluid ounce",
    "pkg": "package",
    "pk": "package",
    "ct": "count",
    "ea": "each",
    "dz": "dozen",
    "sm": "small",
    "md": "medium",
    "lg": "large",
    "xl": "extra large",
    "org": "organic",
    "nat": "natural",
    "ff": "fat free",
    "lf": "low fat",
    "nf": "no fat",
    "sf": "sugar free",
    "ns": "no sugar",
    "gf": "gluten free",
    "df": "dairy free",
    "veg": "vegetarian",
    "vgn": "vegan",
    "pcs": "piece",
    "pc": "piece",
    "btl": "bottle",
    "whl": "whole",
    "conc": "concentrated",
    "past": "pasteurized",
    "refr": "refrigerated",
    "frz": "frozen",
    "envr": "environmentally",
    "sust": "sustainable",
    "rec": "recyclable",
    "w/": "with",
    "w/o": "without",
    "no": "without",
}

try:
    _nlp_model = spacy.load("en_core_web_lg")
except OSError:
    raise RuntimeError(
        "spaCy English model 'en_core_web_lg' not found. "
        "Please ensure the model is installed."
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
    if expansions is None:
        expansions = EXPANSIONS
    if stopwords is None:
        stopwords = STOPWORDS

    # Remove all symbols except alphanumeric
    tokens = [re.sub(r"[^\w]", "", token) for token in tokens]

    # Strip accents if any
    tokens = [
        "".join(
            char
            for char in unicodedata.normalize("NFD", token)
            if unicodedata.category(char) != "Mn"
        )
        for token in tokens
    ]

    # Remove Roman numerals
    tokens = [re.sub(r"^[ivx]+$", "", token) for token in tokens]

    # Split numbers and letters into separate tokens (e.g. 100g -> 100, g)
    split_tokens: list[str] = []
    for token in tokens:
        parts = re.findall(r"\d+|[^\d\s]+", token)
        split_tokens.extend(parts if parts else [token])
    tokens = split_tokens

    # Strip pure numbers
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


class EnglishNormalizer(BaseNormalizer):
    """English text normalizer with instance-level configuration and caching."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize English normalizer with configuration.

        Args:
            config: Optional configuration dict with 'stopwords' and 'expansions' keys
        """
        super().__init__(config or {})

        self.custom_stopwords = None
        self.custom_expansions = None

        if self.config:
            if "stopwords" in self.config:
                self.custom_stopwords = set(self.config["stopwords"])
            if "expansions" in self.config:
                self.custom_expansions = self.config["expansions"]

    def _normalize_uncached(self, text: str) -> list[str]:
        """Perform English normalization without caching.

        Args:
            text: Input text to normalize

        Returns:
            List of normalized tokens
        """
        text = html.unescape(text)
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")

        # Clean leading/trailing punctuation
        text = re.sub(r"^[^\w\s]+|[^\w\s]+$", "", text).strip()

        # Pre-expand abbreviations containing slashes that spaCy would split into punctuation
        active_expansions = (
            self.custom_expansions if self.custom_expansions is not None else EXPANSIONS
        )
        for pattern, replacement in active_expansions.items():
            if "/" in pattern:
                text = re.sub(
                    rf"(?i)(?<!\w){re.escape(pattern)}(?!\w)", replacement, text
                )

        # Title case helps POS tagging on capitalized/mixed receipt text
        normalized_case_text = text.title()
        doc = _nlp_model(normalized_case_text)

        tokens = [
            token.lemma_.lower()
            for token in doc
            if not token.is_punct and not token.is_space
        ]

        return post_process_tokens(
            tokens, self.custom_stopwords, self.custom_expansions
        )
