"""Matching strategies for product matching."""

from .base import MatchingStrategy
from .exact import ExactMatchingStrategy
from .lexical import LexicalMatchingStrategy
from .semantic import SemanticMatchingStrategy

__all__ = [
    "MatchingStrategy",
    "ExactMatchingStrategy",
    "LexicalMatchingStrategy",
    "SemanticMatchingStrategy",
]
