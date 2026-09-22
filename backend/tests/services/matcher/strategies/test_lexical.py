"""Tests for IDF-weighted lexical acceptance."""

from unittest.mock import Mock

from app.services.matcher.context import MatchingContext
from app.services.matcher.strategies.lexical import LexicalMatchingStrategy

FLAVOR_CATALOG = [
    ("gusanitos", "Gusanitos", ["gusanitos"]),
    ("fresas", "Fresas", ["fresa"]),
    ("yogur", "Yogur fresa", ["yogur", "fresa"]),
    ("helado", "Helado fresa", ["helado", "fresa"]),
    ("mermelada", "Mermelada fresa", ["mermelada", "fresa"]),
]


def _context(tokens, aliases):
    backend = Mock()
    backend.language = "es"
    debug = Mock()
    return MatchingContext(
        input_tokens=tokens,
        normalized_input=" ".join(tokens),
        normalized_aliases=aliases,
        backend=backend,
        debug=debug,
    )


class TestLexicalMatchingStrategy:
    def setup_method(self):
        self.strategy = LexicalMatchingStrategy()

    def test_flavor_line_accepts_only_the_snack(self):
        context = _context(["gusanitos", "fresa"], FLAVOR_CATALOG)
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)
        assert result.success is True
        assert result.ambiguous is False
        assert result.matches == [("gusanitos", 1.0)]
        assert result.strategy_name == "Lexical"

    def test_stricter_threshold_does_not_switch_products(self):
        context = _context(["gusanitos", "fresa"], FLAVOR_CATALOG)
        result = self.strategy.match(context, threshold=0.95, max_candidates=5)
        assert result.success is True
        assert result.matches[0][0] == "gusanitos"

    def test_typo_accepts_the_catalog_name(self):
        context = _context(
            ["gusantios"],
            [("gusanitos", "Gusanitos", ["gusanitos"]), ("fresas", "Fresas", ["fresa"])],
        )
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)
        assert result.success is True
        assert result.matches[0][0] == "gusanitos"

    def test_partial_variants_stay_candidates(self):
        context = _context(
            ["leche"],
            [
                ("entera", "Leche entera", ["leche", "entero"]),
                ("desnatada", "Leche desnatada", ["leche", "desnatada"]),
            ],
        )
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)
        assert result.success is False
        assert result.ambiguous is False
        assert {product_id for product_id, _score in result.matches} == {
            "entera",
            "desnatada",
        }

    def test_ambiguous_set_is_not_cut_down_to_max_candidates(self):
        context = _context(
            ["manzana"],
            [("p1", "Manzana", ["manzana"]), ("p2", "Manzana", ["manzana"])],
        )
        # Identical names are an exact-strategy case. Here both names are contained
        # and explain the line equally, so lexical itself must refuse to pick one.
        result = self.strategy.match(context, threshold=0.8, max_candidates=1)
        assert result.success is False
        assert result.ambiguous is True
        assert len(result.matches) == 2

    def test_empty_query_matches_nothing(self):
        context = _context([], FLAVOR_CATALOG)
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)
        assert result.success is False
        assert result.matches == []

    def test_best_alias_per_product_is_kept(self):
        context = _context(
            ["manzana", "golden"],
            [
                ("p1", "Manzana", ["manzana"]),
                ("p1", "Manzana golden", ["manzana", "golden"]),
                ("p2", "Pera", ["pera"]),
            ],
        )
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)
        assert result.success is True
        assert result.matches[0][0] == "p1"
        assert result.aliases["p1"] == "Manzana golden"
