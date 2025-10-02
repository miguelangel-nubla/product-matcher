"""Product matching service with modular strategy-based architecture."""

from .context import MatchingContext, MatchingResult
from .data_preparation import DataPreparation
from .matcher import ProductMatcher
from .pipeline import MatchingPipeline

__all__ = [
    "ProductMatcher",
    "MatchingPipeline",
    "DataPreparation",
    "MatchingContext",
    "MatchingResult",
]
