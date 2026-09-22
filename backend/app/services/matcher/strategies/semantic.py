"""SpaCy suggestions for the review queue. Never accepts a product."""

from ..context import MatchingContext, MatchingResult
from ..scoring import (
    SEMANTIC_SUGGESTION_FLOOR,
    semantic_display_score,
)
from .base import MatchingStrategy


class SemanticMatchingStrategy(MatchingStrategy):
    """Suggest products whose word vectors are near the query.

    Averaged news vectors treat a flavor word as the product. These scores are
    scaled below 0.5 and this strategy always returns success=False, so they
    can fill a review queue without accepting stock movements.
    """

    def get_name(self) -> str:
        return "Semantic"

    def match(
        self, context: MatchingContext, threshold: float, max_candidates: int
    ) -> MatchingResult:
        """Collect semantic suggestions. ``threshold`` is not an accept gate."""

        def _execute() -> MatchingResult:
            context.debug.add(
                f"Starting SpaCy semantic matching setup for {len(context.input_tokens)} input tokens "
                f"(suggestion floor {SEMANTIC_SUGGESTION_FLOOR}; accept threshold {threshold} cannot accept a semantic match)"
            )

            # Get matching utilities for semantic similarity
            from ...matching.utils.registry import get_matching_utils

            matching_utils = get_matching_utils(context.backend.language)

            context.debug.add(
                f"Running semantic similarity calculation on {len(context.normalized_aliases)} pre-normalized aliases"
            )

            best_raw: dict[str, tuple[float, str]] = {}
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
                        "above_threshold": semantic_score >= SEMANTIC_SUGGESTION_FLOOR,
                    }
                )

                if semantic_score > best_raw.get(product_id, (0.0, ""))[0]:
                    best_raw[product_id] = (semantic_score, original_alias)

            suggestions = {
                product_id: (alias, raw)
                for product_id, (raw, alias) in best_raw.items()
                if raw >= SEMANTIC_SUGGESTION_FLOOR
            }
            context.debug.add(
                f"Semantic similarity calculation completed: checked {candidates_checked} aliases, "
                f"found {len(suggestions)} suggestion(s) at or above floor {SEMANTIC_SUGGESTION_FLOOR}",
                all_scores,
            )

            if suggestions:
                ranked = sorted(
                    suggestions.items(), key=lambda item: item[1][1], reverse=True
                )
                selected = ranked[:max_candidates]
                context.debug.add(
                    f"Returning {len(selected)} semantic suggestion(s); none are accepted"
                )
                return MatchingResult(
                    success=False,
                    matches=[
                        (product_id, semantic_display_score(raw))
                        for product_id, (_alias, raw) in selected
                    ],
                    strategy_name=self.get_name(),
                    candidates_checked=candidates_checked,
                    threshold_used=threshold,
                    ambiguous=False,
                    aliases={
                        product_id: alias for product_id, (alias, _raw) in selected
                    },
                )

            context.debug.add(
                f"No semantic suggestions at or above floor {SEMANTIC_SUGGESTION_FLOOR}"
            )
            return MatchingResult(
                success=False,
                matches=[],
                strategy_name=self.get_name(),
                candidates_checked=candidates_checked,
                threshold_used=threshold,
            )

        return self._track_execution_time(_execute)
