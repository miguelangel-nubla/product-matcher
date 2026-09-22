"""Tests for the precision-first matching pipeline."""

from unittest.mock import Mock, patch

from app.services.matcher.context import MatchingContext, MatchingResult
from app.services.matcher.pipeline import MatchingPipeline
from app.services.matcher.scoring import SEMANTIC_DISPLAY_SCALE

FLAVOR_CATALOG = [
    ("gusanitos", "Gusanitos", ["gusanitos"]),
    ("fresas", "Fresas", ["fresa"]),
    ("yogur", "Yogur fresa", ["yogur", "fresa"]),
    ("helado", "Helado fresa", ["helado", "fresa"]),
    ("mermelada", "Mermelada fresa", ["mermelada", "fresa"]),
]


def _context(tokens, aliases, barcodes=None, query_barcodes=None):
    backend = Mock()
    backend.language = "es"
    debug = Mock()
    return MatchingContext(
        input_tokens=tokens,
        normalized_input=" ".join(tokens),
        normalized_aliases=aliases,
        backend=backend,
        debug=debug,
        barcodes=barcodes or {},
        query_barcodes=query_barcodes or [],
    )


class TestMatchingPipeline:
    def setup_method(self):
        self.pipeline = MatchingPipeline()

    def test_init_order(self):
        assert [strategy.get_name() for strategy in self.pipeline.strategies] == [
            "Exact",
            "Lexical",
            "Semantic",
        ]

    def test_flavor_line_accepts_the_snack_and_does_not_ask_embeddings(self):
        context = _context(["gusanitos", "fresa"], FLAVOR_CATALOG)
        with patch.object(self.pipeline.semantic, "match") as semantic_match:
            semantic_match.return_value = MatchingResult(
                success=True,
                matches=[("fresas", 0.95)],
                strategy_name="Semantic",
            )
            success, result = self.pipeline.execute(context, threshold=0.8, max_candidates=5)

        assert success is True
        assert result.matches[0][0] == "gusanitos"
        assert result.strategy_name == "Lexical"
        semantic_match.assert_not_called()

    def test_stricter_threshold_keeps_the_same_product(self):
        context = _context(["gusanitos", "fresa"], FLAVOR_CATALOG)
        with patch.object(self.pipeline.semantic, "match") as semantic_match:
            success, result = self.pipeline.execute(context, threshold=0.95, max_candidates=5)
        assert success is True
        assert result.matches[0][0] == "gusanitos"
        semantic_match.assert_not_called()

    def test_exact_alias_stops_before_lexical_and_semantic(self):
        context = _context(
            ["gusanitos"],
            [("gusanitos", "Gusanitos", ["gusanitos"]), ("fresas", "Fresas", ["fresa"])],
        )
        with (
            patch.object(self.pipeline.lexical, "match") as lexical_match,
            patch.object(self.pipeline.semantic, "match") as semantic_match,
        ):
            success, result = self.pipeline.execute(context, threshold=0.8, max_candidates=5)
        assert success is True
        assert result.strategy_name == "Exact"
        assert result.matches == [("gusanitos", 1.0)]
        lexical_match.assert_not_called()
        semantic_match.assert_not_called()

    def test_exact_ambiguity_is_not_overruled(self):
        context = _context(
            ["manzana"],
            [("p1", "Manzana", ["manzana"]), ("p2", "Manzana", ["manzana"])],
        )
        with patch.object(self.pipeline.lexical, "match") as lexical_match:
            success, result = self.pipeline.execute(context, threshold=0.8, max_candidates=1)
        assert success is False
        assert result.ambiguous is True
        assert len(result.matches) == 2
        lexical_match.assert_not_called()

    def test_synonym_falls_through_to_a_suggestion_and_is_not_accepted(self):
        context = _context(["jitomate"], [("tomate", "Tomate", ["tomate"])])
        suggestion = MatchingResult(
            success=True,
            matches=[("tomate", 0.95)],
            strategy_name="Semantic",
            aliases={"tomate": "Tomate"},
        )
        with patch.object(self.pipeline.semantic, "match", return_value=suggestion):
            success, result = self.pipeline.execute(context, threshold=0.8, max_candidates=5)
        assert success is False
        assert result.ambiguous is False
        assert result.matches[0][0] == "tomate"
        assert result.matches[0][1] <= SEMANTIC_DISPLAY_SCALE
        assert result.strategy_name == "Semantic"

    def test_execute_metrics_logging(self):
        context = _context(["manzana"], [("p1", "Manzana", ["manzana"])])
        self.pipeline.execute(context, threshold=0.8, max_candidates=5)
        debug_calls = [str(call) for call in context.debug.add.call_args_list]
        metrics_log = next((log for log in debug_calls if "processing_time" in log), None)
        assert metrics_log is not None
        assert "candidates_checked=" in metrics_log
