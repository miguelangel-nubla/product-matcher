"""Matching pipeline orchestrator."""

from .context import MatchingContext, MatchingResult
from .scoring import (
    SEMANTIC_DISPLAY_SCALE,
    disambiguate_candidates_by_measurements,
)
from .strategies import (
    ExactMatchingStrategy,
    LexicalMatchingStrategy,
    SemanticMatchingStrategy,
)
from .strategies.base import MatchingStrategy


class MatchingPipeline:
    """Accept on exact keys or lexical coverage. Suggest with embeddings."""

    def __init__(self) -> None:
        self.exact = ExactMatchingStrategy()
        self.lexical = LexicalMatchingStrategy()
        self.semantic = SemanticMatchingStrategy()

    @property
    def strategies(self) -> list[MatchingStrategy]:
        return [self.exact, self.lexical, self.semantic]

    def execute(
        self,
        context: MatchingContext,
        threshold: float = 0.8,
        max_candidates: int = 10,
    ) -> tuple[bool, MatchingResult]:
        """
        Run exact, then lexical, then semantic suggestions.

        Args:
            context: Shared matching context with normalized data
            threshold: Minimum catalog-name coverage required to accept
            max_candidates: Maximum number of candidates to return

        Returns:
            Tuple of (success, final_result). Success is true only for an
            exact key or a lexical accept. Semantic similarity never accepts.
        """
        exact_result = self._run(context, self.exact, threshold, max_candidates)
        if exact_result.success:
            return True, exact_result
        if exact_result.ambiguous and exact_result.matches:
            disambiguated = self._disambiguate_by_measurements(context, exact_result)
            if disambiguated.success:
                return True, disambiguated
            return False, disambiguated

        lexical_result = self._run(context, self.lexical, threshold, max_candidates)
        if lexical_result.success:
            return True, lexical_result
        if lexical_result.ambiguous and lexical_result.matches:
            disambiguated = self._disambiguate_by_measurements(context, lexical_result)
            if disambiguated.success:
                return True, disambiguated
            return False, disambiguated

        semantic_result = self._run(context, self.semantic, threshold, max_candidates)
        merged = self._merge_suggestions(
            lexical_result, semantic_result, max_candidates
        )
        context.debug.add(
            "Semantic suggestions appended; semantic similarity cannot accept a product"
        )
        return False, merged

    def _run(
        self,
        context: MatchingContext,
        strategy: MatchingStrategy,
        threshold: float,
        max_candidates: int,
    ) -> MatchingResult:
        context.debug.add(
            f"Executing {strategy.get_name()} strategy with threshold {threshold}"
        )
        result = strategy.match(context, threshold, max_candidates)
        context.debug.add(
            f"{strategy.get_name()} strategy completed: "
            f"success={result.success}, "
            f"matches={len(result.matches)}, "
            f"candidates_checked={result.candidates_checked}, "
            f"processing_time={result.processing_time_ms:.2f}ms"
        )
        if result.success:
            context.debug.add(
                f"{strategy.get_name()} strategy accepted a product, pipeline completed"
            )
        elif result.ambiguous and result.matches:
            context.debug.add(
                f"{strategy.get_name()} strategy found ambiguous matches, returning them for manual resolution"
            )
        else:
            context.debug.add(
                f"{strategy.get_name()} strategy found no confident match, continuing"
            )
        return result

    def _merge_suggestions(
        self,
        lexical_result: MatchingResult,
        semantic_result: MatchingResult,
        max_candidates: int,
    ) -> MatchingResult:
        """Keep lexical evidence first. Clamp semantic scores so they stay suggestions."""
        seen = {product_id for product_id, _score in lexical_result.matches}
        combined = list(lexical_result.matches)
        aliases = dict(lexical_result.aliases)
        for product_id, score in semantic_result.matches:
            if product_id in seen or len(combined) >= max_candidates:
                continue
            combined.append((product_id, min(score, SEMANTIC_DISPLAY_SCALE)))
            seen.add(product_id)
            alias = semantic_result.aliases.get(product_id)
            if alias:
                aliases[product_id] = alias

        if lexical_result.matches:
            strategy_name = lexical_result.strategy_name
        elif combined:
            strategy_name = semantic_result.strategy_name
        else:
            strategy_name = lexical_result.strategy_name

        return MatchingResult(
            success=False,
            matches=combined,
            strategy_name=strategy_name,
            candidates_checked=(
                lexical_result.candidates_checked + semantic_result.candidates_checked
            ),
            processing_time_ms=(
                lexical_result.processing_time_ms + semantic_result.processing_time_ms
            ),
            threshold_used=lexical_result.threshold_used,
            ambiguous=False,
            aliases=aliases,
        )

    def _disambiguate_by_measurements(
        self, context: MatchingContext, result: MatchingResult
    ) -> MatchingResult:
        """Disambiguate ambiguous ties using measurement, volume, or dimension attributes."""
        if not result.ambiguous or len(result.matches) <= 1:
            return result

        raw_query = context.raw_input or context.normalized_input
        # Build candidate aliases by aggregating original alias texts per product_id
        alias_map: dict[str, list[str]] = {}
        for pid, orig, _ in context.normalized_aliases:
            alias_map.setdefault(pid, []).append(orig)

        candidates: list[tuple[str, str]] = []
        for pid, _ in result.matches:
            orig_texts = alias_map.get(pid, [])
            combined_alias = (
                " ".join(orig_texts) if orig_texts else result.aliases.get(pid, "")
            )
            candidates.append((pid, combined_alias))

        winner_id = disambiguate_candidates_by_measurements(raw_query, candidates)
        if winner_id is not None:
            winner_match = next((m for m in result.matches if m[0] == winner_id), None)
            winner_score = winner_match[1] if winner_match else 1.0
            winner_alias = result.aliases.get(winner_id, "")
            context.debug.add(
                f"Disambiguated ambiguous tie among {len(result.matches)} products to product {winner_id} ('{winner_alias}') via measurement attributes"
            )
            return MatchingResult(
                success=True,
                matches=[(winner_id, winner_score)],
                strategy_name=result.strategy_name,
                candidates_checked=result.candidates_checked,
                processing_time_ms=result.processing_time_ms,
                threshold_used=result.threshold_used,
                ambiguous=False,
                aliases={winner_id: winner_alias},
            )
        return result
