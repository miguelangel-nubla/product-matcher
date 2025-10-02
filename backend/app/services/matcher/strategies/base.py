"""Base abstract class for matching strategies."""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable

from ..context import MatchingContext, MatchingResult


class MatchingStrategy(ABC):
    """Abstract base class for matching strategies.

    Each strategy implements a specific matching algorithm (semantic, fuzzy).
    Strategies are designed to run in order, with earlier strategies having higher confidence.
    """

    @abstractmethod
    def get_name(self) -> str:
        """Return the strategy name for debugging and metrics."""
        pass

    @abstractmethod
    def match(
        self, context: MatchingContext, threshold: float, max_candidates: int
    ) -> MatchingResult:
        """Execute the matching strategy.

        Args:
            context: Shared matching context with normalized data
            threshold: Minimum score threshold for matches
            max_candidates: Maximum number of candidates to return

        Returns:
            MatchingResult with success status, matches, and metrics
        """
        pass

    def _track_execution_time(
        self, func: Callable[[], MatchingResult]
    ) -> MatchingResult:
        """Decorator to track execution time for metrics."""
        start_time = time.time()
        result = func()
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        if hasattr(result, "processing_time_ms"):
            result.processing_time_ms = execution_time
        return result
