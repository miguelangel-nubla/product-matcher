"""Shared score comparison for matching strategies."""

TIE_PRECISION = 3
MAX_AMBIGUOUS_CANDIDATES = 50


def scores_tie(left: float, right: float) -> bool:
    """Treat scores as tied when they match at the displayed precision."""
    return round(left, TIE_PRECISION) == round(right, TIE_PRECISION)


def leading_tie_count(scores: list[float]) -> int:
    """Count the leading run of scores tied with the best score.

    ``scores`` must be sorted descending.
    """
    if not scores:
        return 0
    top = scores[0]
    count = 0
    for score in scores:
        if not scores_tie(score, top):
            break
        count += 1
    return count


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
