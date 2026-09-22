"""IDF-weighted coverage of catalog names, with per-token typo tolerance."""

from ..context import MatchingContext, MatchingResult
from ..scoring import (
    ProductScore,
    score_catalog,
    select_products,
    visible_limit,
)
from .base import MatchingStrategy


class LexicalMatchingStrategy(MatchingStrategy):
    """Accept a product when the line covers its name and no close alternative does.

    Containment is the accept gate: the user threshold is how much of the
    catalog name's distinctive weight must appear in the line. Extra receipt
    words are allowed. Specificity ranks products that all contain their name,
    so a flavor word does not outrank the product that covers the rare token.
    """

    def get_name(self) -> str:
        return "Lexical"

    def match(
        self, context: MatchingContext, threshold: float, max_candidates: int
    ) -> MatchingResult:
        """Score every alias and accept, defer, or return ranked candidates."""

        def _execute() -> MatchingResult:
            context.debug.add(
                f"Starting lexical matching with containment threshold {threshold} "
                f"on {len(context.normalized_aliases)} aliases"
            )
            scores = score_catalog(context.input_tokens, context.normalized_aliases)
            selection = select_products(scores, threshold)
            context.debug.add(
                f"Lexical scoring completed: {len(scores)} products, outcome {selection.outcome}",
                [_score_row(score, threshold) for score in selection.ranked],
            )

            if selection.outcome == "accept" and selection.chosen:
                winner = selection.chosen[0]
                context.debug.add(
                    f"Accepted {winner.product_id} via '{winner.alias}' "
                    f"(containment {winner.containment:.3f}, specificity {winner.specificity:.3f})"
                )
                return self._result(
                    context,
                    threshold,
                    success=True,
                    ambiguous=False,
                    chosen=[winner],
                )

            if selection.outcome == "ambiguous" and selection.chosen:
                limit = visible_limit(
                    total=len(selection.chosen),
                    max_candidates=max_candidates,
                    ambiguous=True,
                    tie_count=len(selection.chosen),
                )
                chosen = selection.chosen[:limit]
                context.debug.add(
                    f"Ambiguous lexical match among {len(selection.chosen)} products, "
                    f"returning {len(chosen)} for manual resolution"
                )
                return self._result(
                    context,
                    threshold,
                    success=False,
                    ambiguous=True,
                    chosen=chosen,
                )

            pool = [score for score in selection.ranked if score.containment > 0]
            chosen = pool[:max_candidates]
            context.debug.add(
                f"No lexical accept; returning {len(chosen)} partial candidate(s)"
            )
            return self._result(
                context,
                threshold,
                success=False,
                ambiguous=False,
                chosen=chosen,
            )

        return self._track_execution_time(_execute)

    def _result(
        self,
        context: MatchingContext,
        threshold: float,
        *,
        success: bool,
        ambiguous: bool,
        chosen: list[ProductScore],
    ) -> MatchingResult:
        return MatchingResult(
            success=success,
            matches=[
                (score.product_id, round(score.containment, 3)) for score in chosen
            ],
            strategy_name=self.get_name(),
            candidates_checked=len(context.normalized_aliases),
            threshold_used=threshold,
            ambiguous=ambiguous,
            aliases={score.product_id: score.alias for score in chosen},
        )


def _score_row(score: ProductScore, threshold: float) -> dict[str, object]:
    return {
        "product_id": score.product_id,
        "alias": score.alias,
        "containment": round(score.containment, 3),
        "specificity": round(score.specificity, 3),
        "fuzzy": score.fuzzy,
        "qualifies": score.containment + 1e-9 >= threshold,
    }
