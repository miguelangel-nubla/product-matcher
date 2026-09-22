"""Tests for barcode keys, token coverage, and the accept decision."""

from app.services.matcher.scoring import (
    ProductScore,
    barcode_key,
    extract_barcodes,
    score_catalog,
    select_products,
    token_similarity,
)

FLAVOR_CATALOG = [
    ("gusanitos", "Gusanitos", ["gusanitos"]),
    ("fresas", "Fresas", ["fresa"]),
    ("yogur", "Yogur fresa", ["yogur", "fresa"]),
    ("helado", "Helado fresa", ["helado", "fresa"]),
    ("mermelada", "Mermelada fresa", ["mermelada", "fresa"]),
]


def test_barcode_key_strips_a_leading_zero_when_eight_digits_remain():
    assert barcode_key("08412345678903") == "8412345678903"
    assert barcode_key("8412345678903") == "8412345678903"


def test_extract_barcodes_ignores_short_numbers():
    assert extract_barcodes("gusanitos 1 pz 8412345678903") == ["8412345678903"]


def test_token_similarity_accepts_a_one_edit_typo_and_rejects_a_synonym():
    assert token_similarity("gusantios", "gusanitos") >= 88
    assert token_similarity("aple", "apple") >= 88
    assert token_similarity("jitomate", "tomate") < 88
    assert token_similarity("roja", "royal") < 88
    assert token_similarity("pan", "paz") == 0


def test_typo_covers_the_catalog_token():
    scores = score_catalog(
        ["gusantios"],
        [("p", "Gusanitos", ["gusanitos"]), ("q", "Fresas", ["fresa"])],
    )
    by_id = {score.product_id: score for score in scores}
    assert by_id["p"].containment == 1
    assert by_id["p"].fuzzy is True
    assert by_id["q"].containment == 0


def test_synonym_does_not_cover_the_catalog_token():
    scores = score_catalog(["jitomate"], [("tomate", "Tomate", ["tomate"])])
    assert scores[0].containment == 0


def test_flavor_line_accepts_the_snack_not_the_ingredient():
    selection = select_products(score_catalog(["gusanitos", "fresa"], FLAVOR_CATALOG), 0.8)
    assert selection.outcome == "accept"
    assert selection.chosen[0].product_id == "gusanitos"


def test_flavor_line_stays_accepted_at_a_stricter_threshold():
    selection = select_products(score_catalog(["gusanitos", "fresa"], FLAVOR_CATALOG), 0.95)
    assert selection.outcome == "accept"
    assert selection.chosen[0].product_id == "gusanitos"


def test_ingredient_alone_accepts_the_ingredient_when_flavored_names_are_mostly_uncovered():
    """'fresa' covers Fresas fully. Yogur fresa is mostly the word yogur, so it does not block."""
    selection = select_products(score_catalog(["fresa"], FLAVOR_CATALOG), 0.8)
    assert selection.outcome == "accept"
    assert selection.chosen[0].product_id == "fresas"


def test_extra_unknown_brand_still_accepts_the_only_contained_name():
    aliases = [
        ("leche", "Leche entera", ["leche", "entero"]),
        ("yogur", "Yogur", ["yogur"]),
        ("pan", "Pan", ["pan"]),
    ]
    selection = select_products(
        score_catalog(["leche", "entero", "pascual"], aliases), 0.8
    )
    assert selection.outcome == "accept"
    assert selection.chosen[0].product_id == "leche"


def test_shared_head_noun_does_not_accept_either_variant():
    aliases = [
        ("entera", "Leche entera", ["leche", "entero"]),
        ("desnatada", "Leche desnatada", ["leche", "desnatada"]),
    ]
    selection = select_products(score_catalog(["leche"], aliases), 0.8)
    assert selection.outcome == "none"
    assert all(score.containment < 0.8 for score in selection.ranked)


def test_specific_name_wins_when_it_covers_the_extra_token():
    aliases = [
        ("manzana", "Manzana", ["manzana"]),
        ("golden", "Manzana golden", ["manzana", "golden"]),
    ]
    selection = select_products(score_catalog(["manzana", "golden"], aliases), 0.8)
    assert selection.outcome == "accept"
    assert selection.chosen[0].product_id == "golden"


def test_higher_specificity_wins_when_both_names_are_contained():
    scores = [
        ProductScore("gusanitos", "Gusanitos", 1.0, 0.7, False),
        ProductScore("fresas", "Fresas", 1.0, 0.3, False),
    ]
    selection = select_products(scores, 0.8)
    assert selection.outcome == "accept"
    assert selection.chosen[0].product_id == "gusanitos"


def test_partial_name_that_explains_the_line_blocks_accept():
    scores = [
        ProductScore("zumo", "Zumo", 1.0, 0.4, False),
        ProductScore("zumo-manzana", "Zumo manzana", 0.6, 1.0, False),
    ]
    selection = select_products(scores, 0.8)
    assert selection.outcome == "ambiguous"
    assert {score.product_id for score in selection.chosen} == {"zumo", "zumo-manzana"}


def test_close_specificity_is_ambiguous():
    scores = [
        ProductScore("a", "A", 1.0, 0.80, False),
        ProductScore("b", "B", 1.0, 0.72, False),
    ]
    selection = select_products(scores, 0.8)
    assert selection.outcome == "ambiguous"


def test_specificity_gap_past_the_margin_accepts():
    scores = [
        ProductScore("a", "A", 1.0, 0.80, False),
        ProductScore("b", "B", 1.0, 0.60, False),
    ]
    selection = select_products(scores, 0.8)
    assert selection.outcome == "accept"
    assert selection.chosen[0].product_id == "a"


def test_generic_is_ambiguous_when_a_longer_name_covers_the_same_tokens():
    scores = [
        ProductScore("manzana", "Manzana", 1.0, 1.0, False),
        ProductScore("golden", "Manzana golden", 0.55, 1.0, False),
    ]
    selection = select_products(scores, 0.8)
    assert selection.outcome == "ambiguous"
    assert selection.chosen[0].product_id == "manzana"


def test_are_plural_forms_and_token_similarity():
    from app.services.matcher.scoring import are_plural_forms

    assert are_plural_forms("uva", "uvas") is True
    assert are_plural_forms("uvas", "uva") is True
    assert are_plural_forms("manzana", "manzanas") is True
    assert are_plural_forms("limon", "limones") is True
    assert are_plural_forms("nuez", "nueces") is True
    assert are_plural_forms("apple", "apples") is True
    assert are_plural_forms("box", "boxes") is True
    assert are_plural_forms("carne", "pescado") is False

    # token_similarity treats plurals as 100.0 exact matches
    assert token_similarity("uva", "uvas") == 100.0
    assert token_similarity("uvas", "uva") == 100.0
    assert token_similarity("manzana", "manzanas") == 100.0
    assert token_similarity("limones", "limon") == 100.0
