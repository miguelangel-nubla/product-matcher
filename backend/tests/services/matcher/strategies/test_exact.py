"""Tests for exact barcode and normalized-alias matching."""

from unittest.mock import Mock

from app.services.matcher.context import MatchingContext
from app.services.matcher.strategies.exact import ExactMatchingStrategy


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


class TestExactMatchingStrategy:
    def setup_method(self):
        self.strategy = ExactMatchingStrategy()

    def test_identical_tokens_accept_regardless_of_order(self):
        context = _context(
            ["jugo", "manzana"],
            [("p1", "Manzana jugo", ["manzana", "jugo"]), ("p2", "Pera", ["pera"])],
        )
        result = self.strategy.match(context, threshold=0.99, max_candidates=5)
        assert result.success is True
        assert result.ambiguous is False
        assert result.matches == [("p1", 1.0)]
        assert result.aliases["p1"] == "Manzana jugo"

    def test_duplicate_normalized_names_are_ambiguous_even_with_one_candidate_slot(self):
        context = _context(
            ["manzana"],
            [("p1", "Manzana", ["manzana"]), ("p2", "MANZANA", ["manzana"])],
        )
        result = self.strategy.match(context, threshold=0.8, max_candidates=1)
        assert result.success is False
        assert result.ambiguous is True
        assert {product_id for product_id, _score in result.matches} == {"p1", "p2"}

    def test_barcode_accepts_when_the_name_was_normalized_away(self):
        context = _context(
            [],
            [("p1", "Gusanitos", ["gusanitos"])],
            barcodes={"p1": "8412345678903"},
            query_barcodes=["8412345678903"],
        )
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)
        assert result.success is True
        assert result.matches == [("p1", 1.0)]

    def test_barcode_and_alias_that_disagree_are_ambiguous(self):
        context = _context(
            ["gusanitos"],
            [
                ("p1", "Gusanitos", ["gusanitos"]),
                ("p2", "Other", ["other"]),
            ],
            barcodes={"p2": "8412345678903"},
            query_barcodes=["8412345678903"],
        )
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)
        assert result.success is False
        assert result.ambiguous is True
        assert {product_id for product_id, _score in result.matches} == {"p1", "p2"}

    def test_no_exact_key_returns_no_match(self):
        context = _context(
            ["gusanitos", "fresa"],
            [("p1", "Gusanitos", ["gusanitos"])],
        )
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)
        assert result.success is False
        assert result.ambiguous is False
        assert result.matches == []

    def test_plural_token_exact_match(self):
        # Singular query matches plural catalog product
        context = _context(
            ["uva"],
            [("p1", "Uvas", ["uvas"]), ("p2", "Pera", ["pera"])],
        )
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)
        assert result.success is True
        assert result.matches == [("p1", 1.0)]

        # Plural query matches singular catalog product
        context_pl = _context(
            ["manzanas"],
            [("p1", "Manzana", ["manzana"])],
        )
        res_pl = self.strategy.match(context_pl, threshold=0.8, max_candidates=5)
        assert res_pl.success is True
        assert res_pl.matches == [("p1", 1.0)]
