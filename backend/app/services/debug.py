"""Debug tracking utilities for matching operations."""

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class DebugStep:
    """Represents a single debug step."""

    message: str
    timestamp: float
    data: Any = None


@dataclass
class MatchingDebugInfo:
    """Complete debug information for a matching operation."""

    steps: list[DebugStep]
    start_time: float

    def to_strings(self) -> list[str]:
        """Convert to list of formatted strings."""
        if not self.steps:
            return []

        result = []
        for i, step in enumerate(self.steps):
            total_ms = (step.timestamp - self.start_time) * 1000
            if i == 0:
                step_ms = total_ms
            else:
                step_ms = (step.timestamp - self.steps[i - 1].timestamp) * 1000

            result.append(f"[{total_ms:.0f}ms +{step_ms:.0f}ms] {step.message}")

        return result

    @property
    def summary(self) -> dict[str, Any]:
        """Return a summary of debug info."""
        if not self.steps:
            return {"total_time_ms": 0, "step_count": 0}

        last_step = self.steps[-1]
        total_time = (last_step.timestamp - self.start_time) * 1000

        return {
            "total_time_ms": total_time,
            "step_count": len(self.steps),
            "steps": [step.message for step in self.steps],
        }


class DebugStepTracker:
    """Tracks debug steps during matching operations."""

    def __init__(self) -> None:
        self.start_time = time.time()
        self.steps: list[DebugStep] = []

    def add(self, message: str, data: Any = None) -> None:
        """Add a debug step."""
        step = DebugStep(message=message, timestamp=time.time(), data=data)
        self.steps.append(step)

    def get_debug_info(self) -> list["DebugStep"]:
        """Get debug info as list of DebugStep objects."""
        return self.steps

    def to_matching_debug_info(self) -> MatchingDebugInfo:
        """Convert to MatchingDebugInfo object."""
        return MatchingDebugInfo(steps=self.steps, start_time=self.start_time)
