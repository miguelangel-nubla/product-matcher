"""Matching strategies for product matching."""

from .base import MatchingStrategy
from .fuzzy import FuzzyMatchingStrategy
from .semantic import SemanticMatchingStrategy

__all__ = [
    "MatchingStrategy",
    "SemanticMatchingStrategy",
    "FuzzyMatchingStrategy",
]
