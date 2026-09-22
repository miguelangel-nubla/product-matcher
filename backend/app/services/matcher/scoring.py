"""Shared score comparison for matching strategies."""

import math
import re
from dataclasses import dataclass
from typing import Literal

from rapidfuzz import fuzz

MAX_AMBIGUOUS_CANDIDATES = 50

# One-edit typos on tokens of length >= 4 score about 88.9. Synonym pairs such
# as jitomate/tomate land just below this and stay suggestions.
TOKEN_FUZZY_RATIO = 88.0
MIN_FUZZY_TOKEN_LENGTH = 4

# A second product this close in specificity is a manual decision, as is a
# partial name that still explains the line. The accept gate itself is the
# caller's containment threshold.
SPECIFICITY_MARGIN = 0.10
PARTIAL_CONTAINMENT_FLOOR = 0.5

# Averaged word-vector similarity is recall for the review queue. Scale it
# under 0.5 so a suggestion cannot display as an accepted match.
SEMANTIC_DISPLAY_SCALE = 0.49
SEMANTIC_SUGGESTION_FLOOR = 0.45

_BARCODE_RE = re.compile(r"\d{8,14}")


def visible_limit(
    *, total: int, max_candidates: int, ambiguous: bool, tie_count: int
) -> int:
    """How many ranked matches to return.

    A unique winner respects ``max_candidates``. An ambiguous tie includes
    every tied product, up to a hard cap, so the caller can resolve it.
    """
    if total <= 0:
        return 0
    if ambiguous:
        return min(total, max(max_candidates, min(tie_count, MAX_AMBIGUOUS_CANDIDATES)))
    return min(total, max_candidates)


def barcode_key(value: str) -> str:
    """Normalize a barcode to comparable digits.

    Leading zeros are stripped when at least 8 digits remain, so a UPC and the
    EAN-13 formed by prefixing zero compare equal. Shorter remnants keep their
    original digits and fail the caller's length check.
    """
    digits = re.sub(r"\D", "", value)
    stripped = digits.lstrip("0")
    if len(stripped) >= 8:
        return stripped
    return digits


def extract_barcodes(text: str) -> list[str]:
    """Return unique barcode keys found as contiguous digit runs in ``text``."""
    found: list[str] = []
    seen: set[str] = set()
    for raw in _BARCODE_RE.findall(text or ""):
        key = barcode_key(raw)
        if len(key) < 8 or key in seen:
            continue
        seen.add(key)
        found.append(key)
    return found


def are_plural_forms(a: str, b: str) -> bool:
    """Return True if one string is a standard grammatical plural of the other.

    Handles:
    - Standard -s addition (e.g., uva/uvas, manzana/manzanas, apple/apples)
    - Standard -es addition (e.g., limon/limones, yogur/yogures, box/boxes)
    - Spanish -ces vs -z (e.g., nuez/nueces, pez/peces, raiz/raices)
    """
    if not a or not b or a == b:
        return False
    shorter, longer = (a, b) if len(a) < len(b) else (b, a)
    if longer == shorter + "s":
        return True
    if longer == shorter + "es":
        return True
    if longer.endswith("ces") and shorter.endswith("z") and longer[:-3] == shorter[:-1]:
        return True
    return False


def token_similarity(left: str, right: str) -> float:
    """Return 100 for an equal or plural token, else a typo score, else 0.

    Tokens shorter than ``MIN_FUZZY_TOKEN_LENGTH`` do not fuzzy-match. One
    edit on a short token collides with unrelated words.
    Plural forms are considered exact matches (score 100.0).
    """
    if left == right or are_plural_forms(left, right):
        return 100.0
    if len(left) < MIN_FUZZY_TOKEN_LENGTH or len(right) < MIN_FUZZY_TOKEN_LENGTH:
        return 0.0
    return float(fuzz.ratio(left, right))


def semantic_display_score(raw: float) -> float:
    """Scale a semantic similarity into the suggestion range."""
    return round(raw * SEMANTIC_DISPLAY_SCALE, 3)


@dataclass(frozen=True)
class ProductScore:
    """Best alias score for one catalog product."""

    product_id: str
    alias: str
    containment: float
    specificity: float
    fuzzy: bool

    @property
    def rank(self) -> float:
        """How completely this product explains the line."""
        return self.containment * self.specificity


@dataclass(frozen=True)
class Selection:
    """Accept decision over a scored catalog."""

    outcome: Literal["accept", "ambiguous", "none"]
    chosen: list[ProductScore]
    ranked: list[ProductScore]


def _idf(df: int, n_products: int) -> float:
    return math.log((n_products + 1) / (df + 1)) + 1.0


def build_idf(
    aliases: list[tuple[str, str, list[str]]],
) -> tuple[dict[str, float], float]:
    """IDF of each token, counting a product once no matter how many aliases it has.

    The default weight is the IDF of a token that appears in no product. Unknown
    receipt words are heavier than any catalog word, so an unexplained rare
    token lowers specificity without inventing a product.
    """
    products: dict[str, set[str]] = {}
    for product_id, _alias, tokens in aliases:
        bucket = products.setdefault(product_id, set())
        bucket.update(tokens)
    n_products = len(products) or 1
    document_frequency: dict[str, int] = {}
    for product_tokens in products.values():
        for token in product_tokens:
            document_frequency[token] = document_frequency.get(token, 0) + 1
    weights = {
        token: _idf(count, n_products) for token, count in document_frequency.items()
    }
    return weights, _idf(0, n_products)


def _weight(token: str, weights: dict[str, float], default_idf: float) -> float:
    return weights.get(token, default_idf)


def score_alias(
    query_tokens: list[str],
    alias_tokens: list[str],
    weights: dict[str, float],
    default_idf: float,
) -> tuple[float, float, bool]:
    """Return containment, specificity, and whether a typo alignment was used.

    Containment is the fraction of the alias's IDF weight covered by the query.
    Specificity is the fraction of the query's IDF weight covered by the alias.
    Each token is used at most once. Exact tokens are aligned before typos.
    """
    if not query_tokens or not alias_tokens:
        return 0.0, 0.0, False

    pairs: list[tuple[float, int, int]] = []
    for query_index, query_token in enumerate(query_tokens):
        for alias_index, alias_token in enumerate(alias_tokens):
            similarity = token_similarity(query_token, alias_token)
            if similarity >= TOKEN_FUZZY_RATIO:
                pairs.append((similarity, query_index, alias_index))
    pairs.sort(key=lambda item: (-item[0], item[1], item[2]))

    used_query: set[int] = set()
    used_alias: set[int] = set()
    matched_query = 0.0
    matched_alias = 0.0
    fuzzy = False
    for similarity, query_index, alias_index in pairs:
        if query_index in used_query or alias_index in used_alias:
            continue
        used_query.add(query_index)
        used_alias.add(alias_index)
        if similarity < 100.0:
            fuzzy = True
        matched_query += _weight(query_tokens[query_index], weights, default_idf)
        matched_alias += _weight(alias_tokens[alias_index], weights, default_idf)

    query_total = sum(_weight(token, weights, default_idf) for token in query_tokens)
    alias_total = sum(_weight(token, weights, default_idf) for token in alias_tokens)
    containment = matched_alias / alias_total if alias_total else 0.0
    specificity = matched_query / query_total if query_total else 0.0
    return containment, specificity, fuzzy


def score_catalog(
    query_tokens: list[str],
    aliases: list[tuple[str, str, list[str]]],
) -> list[ProductScore]:
    """Score each product by its best alias. Empty queries score nothing."""
    if not query_tokens or not aliases:
        return []
    weights, default_idf = build_idf(aliases)
    best: dict[str, ProductScore] = {}
    for product_id, alias, alias_tokens in aliases:
        if not alias_tokens:
            continue
        containment, specificity, fuzzy = score_alias(
            query_tokens, alias_tokens, weights, default_idf
        )
        candidate = ProductScore(
            product_id=product_id,
            alias=alias,
            containment=containment,
            specificity=specificity,
            fuzzy=fuzzy,
        )
        current = best.get(product_id)
        if current is None or (candidate.containment, candidate.specificity) > (
            current.containment,
            current.specificity,
        ):
            best[product_id] = candidate
    return list(best.values())


def _meets(value: float, cutoff: float) -> bool:
    return value + 1e-9 >= cutoff


def select_products(scores: list[ProductScore], threshold: float) -> Selection:
    """Choose an accept, an ambiguous set, or no accept.

    A product qualifies when its catalog name is covered to ``threshold``
    (containment). Extra words on the line are allowed. Among qualifiers, the
    product that covers more of the line's distinctive weight wins. A near
    second place, including a partial name that explains the line as well,
    is returned for manual resolution instead of being accepted.
    """
    ranked = sorted(
        scores,
        key=lambda score: (score.rank, score.containment, score.specificity),
        reverse=True,
    )
    qualifiers = [score for score in scores if _meets(score.containment, threshold)]
    if not qualifiers:
        return Selection(outcome="none", chosen=[], ranked=ranked)

    qualifiers.sort(
        key=lambda score: (score.specificity, score.containment), reverse=True
    )
    best = qualifiers[0]
    rivals = [
        score
        for score in scores
        if score.product_id != best.product_id
        and _meets(score.specificity, best.specificity - SPECIFICITY_MARGIN)
        and (
            _meets(score.containment, PARTIAL_CONTAINMENT_FLOOR)
            or _meets(score.containment, threshold)
        )
    ]
    if rivals:
        chosen = [best, *rivals]
        chosen.sort(
            key=lambda score: (score.rank, score.containment, score.specificity),
            reverse=True,
        )
        return Selection(outcome="ambiguous", chosen=chosen, ranked=ranked)
    return Selection(outcome="accept", chosen=[best], ranked=ranked)
