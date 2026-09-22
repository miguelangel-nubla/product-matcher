"""Order-sensitive, bounded cache for semantic similarity scores."""

from collections import OrderedDict
from collections.abc import Callable
from typing import Any

MAX_SEMANTIC_CACHE_SIZE = 4096


def cache_key(tokens1: list[str], tokens2: list[str]) -> str:
    """Build a symmetric cache key that preserves token order on each side."""
    left = "\x1f".join(tokens1)
    right = "\x1f".join(tokens2)
    if left <= right:
        return f"{left}\x1e{right}"
    return f"{right}\x1e{left}"


def calculate_semantic_similarity(
    cache: OrderedDict[str, float],
    tokens1: list[str],
    tokens2: list[str],
    nlp: Callable[[str], Any],
    doc1: Any | None = None,
    max_size: int = MAX_SEMANTIC_CACHE_SIZE,
) -> float:
    """Score two token sequences and remember the result.

    Identical sequences score 1.0. Different orders are different inputs.
    Swapping the two sequences shares one cache entry because similarity is
    symmetric. The cache evicts the oldest entries past ``max_size``.
    """
    if not tokens1 or not tokens2:
        return 0.0
    if tokens1 == tokens2:
        return 1.0

    key = cache_key(tokens1, tokens2)
    cached = cache.get(key)
    if cached is not None:
        cache.move_to_end(key)
        return cached

    text1 = " ".join(tokens1)
    text2 = " ".join(tokens2)
    if not text1.strip() or not text2.strip():
        return 0.0

    if doc1 is None:
        doc1 = nlp(text1)
    doc2 = nlp(text2)
    score = float(doc1.similarity(doc2))

    cache[key] = score
    cache.move_to_end(key)
    while len(cache) > max_size:
        cache.popitem(last=False)
    return score
