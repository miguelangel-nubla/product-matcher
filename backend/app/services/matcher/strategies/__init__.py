"""Matching strategies for product matching."""

from .base import MatchingStrategy
from .fuzzy import FuzzyMatchingStrategy
from .jaccard import JaccardMatchingStrategy
from .semantic import SemanticMatchingStrategy

__all__ = [
    "MatchingStrategy",
    "JaccardMatchingStrategy",
    "SemanticMatchingStrategy",
    "FuzzyMatchingStrategy",
]
