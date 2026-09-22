"""Exact barcode and normalized-alias matching."""

from collections import Counter

from ..context import MatchingContext, MatchingResult
from ..scoring import visible_limit
from .base import MatchingStrategy


def _token_key(tokens: list[str]) -> tuple[tuple[str, int], ...]:
    """Order-independent identity of a token multiset."""
    if not tokens:
        return ()
    return tuple(sorted(Counter(tokens).items()))


class ExactMatchingStrategy(MatchingStrategy):
    """Accept a product only when an exact key hits.

    A barcode on the line, or a normalized alias whose tokens equal the query,
    is sufficient. Graded similarity is not consulted. Several products sharing
    the key are returned for manual resolution.
    """

    def get_name(self) -> str:
        return "Exact"

    def match(
        self, context: MatchingContext, threshold: float, max_candidates: int
    ) -> MatchingResult:
        """Match barcodes and identical normalized aliases."""

        def _execute() -> MatchingResult:
            context.debug.add(
                f"Starting exact matching (accept threshold {threshold} is not applied to exact keys)"
            )
            barcode_hits = self._barcode_hits(context)
            name_hits = self._name_hits(context)
            context.debug.add(
                f"Exact keys: {len(barcode_hits)} barcode hit(s), {len(name_hits)} alias hit(s)",
                {
                    "barcode_product_ids": sorted(barcode_hits),
                    "alias_product_ids": sorted(name_hits),
                },
            )

            if barcode_hits and name_hits and set(barcode_hits) != set(name_hits):
                return self._ambiguous(
                    context,
                    threshold,
                    max_candidates,
                    {**name_hits, **barcode_hits},
                    "Barcode and alias keys identify different products",
                )
            hits = barcode_hits or name_hits
            if len(hits) == 1:
                product_id, alias = next(iter(hits.items()))
                context.debug.add(f"Exact match on product {product_id} via '{alias}'")
                return MatchingResult(
                    success=True,
                    matches=[(product_id, 1.0)],
                    strategy_name=self.get_name(),
                    candidates_checked=len(context.normalized_aliases),
                    threshold_used=threshold,
                    aliases={product_id: alias},
                )
            if len(hits) > 1:
                return self._ambiguous(
                    context,
                    threshold,
                    max_candidates,
                    hits,
                    "Several products share this exact key",
                )

            context.debug.add("No exact barcode or alias match")
            return MatchingResult(
                success=False,
                matches=[],
                strategy_name=self.get_name(),
                candidates_checked=len(context.normalized_aliases),
                threshold_used=threshold,
            )

        return self._track_execution_time(_execute)

    def _barcode_hits(self, context: MatchingContext) -> dict[str, str]:
        wanted = set(context.query_barcodes)
        if not wanted:
            return {}
        hits: dict[str, str] = {}
        for product_id, code in context.barcodes.items():
            if code in wanted:
                hits[product_id] = self._label(context, product_id, code)
        return hits

    def _name_hits(self, context: MatchingContext) -> dict[str, str]:
        query_key = _token_key(context.input_tokens)
        if not query_key:
            return {}
        hits: dict[str, str] = {}
        for product_id, alias, tokens in context.normalized_aliases:
            if _token_key(tokens) == query_key:
                hits.setdefault(product_id, alias)
        return hits

    def _label(self, context: MatchingContext, product_id: str, barcode: str) -> str:
        for candidate_id, alias, _tokens in context.normalized_aliases:
            if candidate_id == product_id and alias:
                return alias
        return barcode

    def _ambiguous(
        self,
        context: MatchingContext,
        threshold: float,
        max_candidates: int,
        hits: dict[str, str],
        reason: str,
    ) -> MatchingResult:
        ordered = sorted(hits.items())
        limit = visible_limit(
            total=len(ordered),
            max_candidates=max_candidates,
            ambiguous=True,
            tie_count=len(ordered),
        )
        selected = ordered[:limit]
        context.debug.add(
            f"{reason}: {len(hits)} products, returning {len(selected)} for manual resolution"
        )
        return MatchingResult(
            success=False,
            matches=[(product_id, 1.0) for product_id, _alias in selected],
            strategy_name=self.get_name(),
            candidates_checked=len(context.normalized_aliases),
            threshold_used=threshold,
            ambiguous=True,
            aliases=dict(selected),
        )
