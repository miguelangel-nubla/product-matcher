"""Fuzzy string matching strategy using fuzzywuzzy."""

from rapidfuzz import fuzz

from ..context import MatchingContext, MatchingResult
from .base import MatchingStrategy


class FuzzyMatchingStrategy(MatchingStrategy):
    """Fuzzy string matching strategy.

    Lower confidence strategy - returns top candidates based on fuzzy string similarity.
    Good for catching variations with typos, abbreviations, or slight differences.
    """

    def get_name(self) -> str:
        return "Fuzzy"

    def match(
        self, context: MatchingContext, threshold: float, max_candidates: int
    ) -> MatchingResult:
        """Execute fuzzy string matching."""

        def _execute() -> MatchingResult:
            context.debug.add(
                f"Starting fuzzy matching with threshold {threshold} on {len(context.normalized_aliases)} pre-normalized aliases"
            )

            input_text = " ".join(context.input_tokens)

            # Store all fuzzy calculations for examples
            all_fuzzy_scores = []
            product_best_scores: dict[
                str, tuple[str, float, list[str]]
            ] = {}  # Track best score per product
            candidates_checked = 0

            for product_id, original_alias, alias_tokens in context.normalized_aliases:
                candidates_checked += 1
                alias_text = " ".join(alias_tokens)

                if input_text and alias_text:
                    fuzzy_score = fuzz.token_sort_ratio(input_text, alias_text) / 100.0
                    all_fuzzy_scores.append(
                        (
                            input_text,
                            alias_text,
                            fuzzy_score,
                            original_alias,
                            product_id,
                        )
                    )

                    # Track best score for this product
                    if (
                        product_id not in product_best_scores
                        or fuzzy_score > product_best_scores[product_id][1]
                    ):
                        product_best_scores[product_id] = (
                            original_alias,
                            fuzzy_score,
                            alias_tokens,
                        )

            # Show all fuzzy matching calculations
            fuzzy_data = [
                {
                    "query": query,
                    "normalized_alias": alias,
                    "score": round(score, 3),
                    "original_alias": orig,
                    "product_id": pid,
                }
                for query, alias, score, orig, pid in all_fuzzy_scores
            ]
            context.debug.add(
                f"Fuzzy matching calculation completed: processed {len(all_fuzzy_scores)} comparisons",
                fuzzy_data,
            )

            # Collect all products with their best scores
            all_scored_matches = [
                (product_id, best_score)
                for product_id, (_, best_score, _) in product_best_scores.items()
            ]

            # Sort by score (descending) and take top candidates
            all_scored_matches.sort(key=lambda x: x[1], reverse=True)
            top_candidates = all_scored_matches[:max_candidates]

            # Count how many are above threshold for logging
            above_threshold_count = sum(
                1 for _, score in top_candidates if score >= threshold
            )

            context.debug.add(
                f"Found {above_threshold_count} products above threshold {threshold} from {len(context.normalized_aliases)} pre-normalized aliases, returning top {len(top_candidates)} candidates"
            )

            # Check for success based on matches above threshold
            above_threshold_matches = [
                match for match in top_candidates if match[1] >= threshold
            ]

            if len(above_threshold_matches) > 1:
                top_score = above_threshold_matches[0][1]
                top_score_count = sum(
                    1 for _, score in above_threshold_matches if score == top_score
                )
                if top_score_count > 1:
                    context.debug.add(
                        f"Found {top_score_count} products with identical top score {top_score:.3f} above threshold - treating as no match due to ambiguity"
                    )
                    success = False
                else:
                    context.debug.add(
                        f"Single best match found above threshold with score {top_score:.3f}"
                    )
                    success = True
            elif len(above_threshold_matches) == 1:
                context.debug.add(
                    f"Single match found above threshold with score {above_threshold_matches[0][1]:.3f}"
                )
                success = True
            else:
                context.debug.add("No matches found above threshold")
                success = False

            context.debug.add(
                f"Returning top {len(top_candidates)} candidates (success: {success})"
            )

            return MatchingResult(
                success=success,
                matches=top_candidates,
                strategy_name=self.get_name(),
                candidates_checked=candidates_checked,
                threshold_used=threshold,
            )

        return self._track_execution_time(_execute)
