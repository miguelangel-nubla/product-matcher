"""Matching pipeline orchestrator."""

from .context import MatchingContext, MatchingResult
from .strategies import FuzzyMatchingStrategy, SemanticMatchingStrategy


class MatchingPipeline:
    """Orchestrates the execution of matching strategies in order."""

    def __init__(self) -> None:
        # Define strategy order: higher confidence strategies first
        self.strategies = [
            SemanticMatchingStrategy(),
            FuzzyMatchingStrategy(),
        ]

    def execute(
        self,
        context: MatchingContext,
        semantic_threshold: float = 0.6,
        fuzzy_threshold: float = 0.8,
        max_candidates: int = 10,
    ) -> tuple[bool, MatchingResult]:
        """
        Execute the matching pipeline with different thresholds per strategy.

        Args:
            context: Shared matching context with normalized data
            semantic_threshold: Threshold for semantic similarity matching
            fuzzy_threshold: Threshold for fuzzy string matching
            max_candidates: Maximum number of candidates to return

        Returns:
            Tuple of (success, final_result)
        """
        # Map strategy names to their thresholds
        strategy_thresholds = {
            "Semantic": semantic_threshold,
            "Fuzzy": fuzzy_threshold,
        }

        for strategy in self.strategies:
            threshold = strategy_thresholds.get(strategy.get_name(), fuzzy_threshold)

            context.debug.add(
                f"Executing {strategy.get_name()} strategy with threshold {threshold}"
            )

            result = strategy.match(context, threshold, max_candidates)

            # Log strategy execution metrics
            context.debug.add(
                f"{strategy.get_name()} strategy completed: "
                f"success={result.success}, "
                f"matches={len(result.matches)}, "
                f"candidates_checked={result.candidates_checked}, "
                f"processing_time={result.processing_time_ms:.2f}ms"
            )

            if result.success:
                context.debug.add(
                    f"{strategy.get_name()} strategy found matches, pipeline completed"
                )
                return True, result

            context.debug.add(
                f"{strategy.get_name()} strategy found no matches, continuing to next strategy"
            )

        # No strategy succeeded
        context.debug.add("All strategies completed without finding matches")

        # Return the last result (fuzzy) with success=False
        return False, result
