"""Data classes for matching context and results."""

from dataclasses import dataclass
from typing import Any

from app.services.backend import Backend

# Import will be added after DebugStepTracker is moved to shared location


@dataclass
class MatchingContext:
    """Shared context for all matching strategies."""

    input_tokens: list[str]
    normalized_input: str
    normalized_aliases: list[
        tuple[str, str, list[str]]
    ]  # (product_id, original_alias, tokens)
    backend: Backend
    debug: Any  # DebugStepTracker - will be properly typed after refactor


@dataclass
class MatchingResult:
    """Result from a matching strategy."""

    success: bool
    matches: list[tuple[str, float]]  # (product_id, score)
    strategy_name: str

    # Metrics for monitoring
    candidates_checked: int = 0
    processing_time_ms: float = 0.0
    threshold_used: float = 0.0
