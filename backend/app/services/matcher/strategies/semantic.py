"""SpaCy semantic similarity matching strategy."""

from ..context import MatchingContext, MatchingResult
from ..scoring import leading_tie_count, visible_limit
from .base import MatchingStrategy


class SemanticMatchingStrategy(MatchingStrategy):
    """SpaCy semantic similarity matching strategy.

    Medium confidence strategy - returns best semantic matches when available.
    Good for finding semantically related products even with different terminology.
    """

    def get_name(self) -> str:
        return "Semantic"

    def match(
        self, context: MatchingContext, threshold: float, max_candidates: int
    ) -> MatchingResult:
        """Execute SpaCy semantic similarity matching."""

        def _execute() -> MatchingResult:
            context.debug.add(
                f"Starting SpaCy semantic matching setup for {len(context.input_tokens)} input tokens"
            )

            # Get matching utilities for semantic similarity
            from ...matching.utils.registry import get_matching_utils

            matching_utils = get_matching_utils(context.backend.language)

            context.debug.add(
                f"Running semantic similarity calculation on {len(context.normalized_aliases)} pre-normalized aliases"
            )

            product_scores: dict[
                str, tuple[str, float]
            ] = {}  # Track best score per product
            candidates_checked = 0
            all_scores = []  # Track all scores for debug

            input_doc = (
                matching_utils.get_doc(context.input_tokens)
                if hasattr(matching_utils, "get_doc")
                else None
            )

            for product_id, original_alias, alias_tokens in context.normalized_aliases:
                candidates_checked += 1
                semantic_score = matching_utils.calculate_semantic_similarity(
                    context.input_tokens, alias_tokens, doc1=input_doc
                )

                # Record all scores for debug
                all_scores.append(
                    {
                        "product_id": product_id,
                        "original_alias": original_alias,
                        "alias_tokens": alias_tokens,
                        "score": round(semantic_score, 3),
                        "above_threshold": semantic_score >= threshold,
                    }
                )

                if semantic_score >= threshold:
                    # Track best score for this product
                    if (
                        product_id not in product_scores
                        or semantic_score > product_scores[product_id][1]
                    ):
                        product_scores[product_id] = (original_alias, semantic_score)

            context.debug.add(
                f"Semantic similarity calculation completed: checked {candidates_checked} aliases, found {len(product_scores)} products with matches above threshold {threshold}",
                all_scores,
            )

            # If semantic matches found, return them (medium confidence)
            if len(product_scores) >= 1:
                # Sort by score. Detect ties on the full above-threshold list
                # before applying the candidate limit.
                sorted_matches = sorted(
                    product_scores.items(), key=lambda x: x[1][1], reverse=True
                )
                ranked_scores = [score for _, (_, score) in sorted_matches]
                tie_count = leading_tie_count(ranked_scores)
                ambiguous = tie_count > 1
                limit = visible_limit(
                    total=len(sorted_matches),
                    max_candidates=max_candidates,
                    ambiguous=ambiguous,
                    tie_count=tie_count,
                )
                selected = sorted_matches[:limit]
                top_matches = [
                    (product_id, score) for product_id, (_, score) in selected
                ]
                aliases = {
                    product_id: alias for product_id, (alias, _) in selected
                }

                if ambiguous:
                    context.debug.add(
                        f"Found {tie_count} products with tied top semantic score {ranked_scores[0]:.3f} above threshold - treating as ambiguous (success=False)"
                    )
                else:
                    context.debug.add(
                        f"Found {len(product_scores)} products via SpaCy semantic similarity (threshold: {threshold}) - returning semantic matches"
                    )

                return MatchingResult(
                    success=not ambiguous,
                    matches=top_matches,
                    strategy_name=self.get_name(),
                    candidates_checked=candidates_checked,
                    threshold_used=threshold,
                    ambiguous=ambiguous,
                    aliases=aliases,
                )
            else:
                context.debug.add(
                    f"No products matched via SpaCy semantic similarity (threshold: {threshold}), continuing to next strategy"
                )

            return MatchingResult(
                success=False,
                matches=[],
                strategy_name=self.get_name(),
                candidates_checked=candidates_checked,
                threshold_used=threshold,
            )

        return self._track_execution_time(_execute)
