"""Jaccard token overlap matching strategy."""

from ..context import MatchingContext, MatchingResult
from .base import MatchingStrategy


def calculate_jaccard_similarity(tokens1: list[str], tokens2: list[str]) -> float:
    """
    Calculate Jaccard similarity (token overlap) between two token lists.

    Args:
        tokens1: First set of tokens
        tokens2: Second set of tokens

    Returns:
        Jaccard similarity score (0.0 to 1.0)
    """
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0

    set1 = set(tokens1)
    set2 = set(tokens2)

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union if union > 0 else 0.0


class JaccardMatchingStrategy(MatchingStrategy):
    """Exact token overlap matching strategy.

    Highest confidence strategy - returns immediately if exactly one product
    passes the threshold. Best for exact product matches.
    """

    def get_name(self) -> str:
        return "Jaccard"

    def match(
        self, context: MatchingContext, threshold: float, max_candidates: int
    ) -> MatchingResult:
        """Execute Jaccard token overlap matching."""

        def _execute() -> MatchingResult:
            context.debug.add(
                f"Starting Jaccard token overlap matching for {len(context.input_tokens)} input tokens"
            )

            context.debug.add(
                f"Running Jaccard similarity calculation on {len(context.normalized_aliases)} pre-normalized aliases"
            )

            product_scores: dict[
                str, tuple[str, float]
            ] = {}  # Track best score per product
            candidates_checked = 0
            all_scores = []  # Track all scores for debug

            for product_id, original_alias, alias_tokens in context.normalized_aliases:
                candidates_checked += 1
                overlap_score = calculate_jaccard_similarity(
                    context.input_tokens, alias_tokens
                )

                # Record all scores for debug
                all_scores.append(
                    {
                        "product_id": product_id,
                        "original_alias": original_alias,
                        "alias_tokens": alias_tokens,
                        "score": round(overlap_score, 3),
                        "above_threshold": overlap_score >= threshold,
                    }
                )

                if overlap_score >= threshold:
                    context.debug.add(
                        f"  Jaccard match found: '{original_alias}' -> {alias_tokens} (score: {overlap_score:.3f})"
                    )

                    # Track best score for this product (multiple aliases of same product is fine)
                    if (
                        product_id not in product_scores
                        or overlap_score > product_scores[product_id][1]
                    ):
                        product_scores[product_id] = (original_alias, overlap_score)

            context.debug.add(
                f"Jaccard similarity calculation completed: checked {candidates_checked} aliases, found {len(product_scores)} products with matches above threshold {threshold}",
                all_scores,
            )

            # Jaccard strategy: return success only if exactly ONE product matches (high confidence)
            if len(product_scores) == 1:
                product_id, (best_alias, best_score) = list(product_scores.items())[0]
                context.debug.add(
                    f"Exactly 1 product matched via Jaccard ('{best_alias}' score: {best_score:.3f} >= {threshold}) - returning high confidence result"
                )
                matches = [(product_id, best_score)]
                return MatchingResult(
                    success=True,
                    matches=matches,
                    strategy_name=self.get_name(),
                    candidates_checked=candidates_checked,
                    threshold_used=threshold,
                )
            elif len(product_scores) > 1:
                context.debug.add(
                    f"Multiple products matched via Jaccard ({len(product_scores)} products >= {threshold}), continuing to next strategy"
                )
            else:
                context.debug.add(
                    f"No products matched via Jaccard (threshold: {threshold}), continuing to next strategy"
                )

            return MatchingResult(
                success=False,
                matches=[],
                strategy_name=self.get_name(),
                candidates_checked=candidates_checked,
                threshold_used=threshold,
            )

        return self._track_execution_time(_execute)
