"""Test cases for the debug tracking services."""

import time
import pytest
from unittest.mock import patch

from app.services.debug import DebugStepTracker, MatchingDebugInfo
from app.models import DebugStep


class TestDebugStepTracker:
    """Test cases for DebugStepTracker."""

    def test_init(self):
        """Test DebugStepTracker initialization."""
        tracker = DebugStepTracker()

        assert isinstance(tracker.start_time, float)
        assert tracker.steps == []
        assert tracker.start_time <= time.time()

    def test_add_message_only(self):
        """Test adding a debug step with message only."""
        tracker = DebugStepTracker()

        tracker.add("Test message")

        assert len(tracker.steps) == 1
        step = tracker.steps[0]
        assert isinstance(step, DebugStep)
        assert step.message == "Test message"
        assert step.data is None
        assert isinstance(step.timestamp, float)
        assert step.timestamp >= tracker.start_time

    def test_add_message_with_data(self):
        """Test adding a debug step with message and data."""
        tracker = DebugStepTracker()
        test_data = {"key": "value", "number": 42}

        tracker.add("Test message with data", test_data)

        assert len(tracker.steps) == 1
        step = tracker.steps[0]
        assert step.message == "Test message with data"
        assert step.data == test_data

    def test_add_multiple_steps(self):
        """Test adding multiple debug steps."""
        tracker = DebugStepTracker()

        tracker.add("First step")
        tracker.add("Second step", {"data": "value"})
        tracker.add("Third step")

        assert len(tracker.steps) == 3
        assert tracker.steps[0].message == "First step"
        assert tracker.steps[1].message == "Second step"
        assert tracker.steps[2].message == "Third step"

        # Verify timestamps are in order
        assert tracker.steps[0].timestamp <= tracker.steps[1].timestamp
        assert tracker.steps[1].timestamp <= tracker.steps[2].timestamp

    def test_get_debug_info(self):
        """Test getting debug info as list."""
        tracker = DebugStepTracker()
        tracker.add("Test step 1")
        tracker.add("Test step 2")

        debug_info = tracker.get_debug_info()

        assert debug_info == tracker.steps
        assert len(debug_info) == 2
        assert all(isinstance(step, DebugStep) for step in debug_info)

    def test_get_debug_info_empty(self):
        """Test getting debug info when no steps added."""
        tracker = DebugStepTracker()

        debug_info = tracker.get_debug_info()

        assert debug_info == []

    def test_to_matching_debug_info(self):
        """Test conversion to MatchingDebugInfo."""
        tracker = DebugStepTracker()
        tracker.add("Test step")

        matching_debug = tracker.to_matching_debug_info()

        assert isinstance(matching_debug, MatchingDebugInfo)
        assert matching_debug.steps == tracker.steps
        assert matching_debug.start_time == tracker.start_time

    @patch('time.time')
    def test_timestamp_consistency(self, mock_time):
        """Test that timestamps are consistent."""
        # Mock time.time to return predictable values
        mock_time.side_effect = [1000.0, 1001.0, 1002.0]

        tracker = DebugStepTracker()
        assert tracker.start_time == 1000.0

        tracker.add("Step 1")
        assert tracker.steps[0].timestamp == 1001.0

        tracker.add("Step 2")
        assert tracker.steps[1].timestamp == 1002.0


class TestMatchingDebugInfo:
    """Test cases for MatchingDebugInfo."""

    def create_debug_steps(self, start_time=1000.0):
        """Helper to create test debug steps."""
        return [
            DebugStep(message="First step", timestamp=start_time + 0.1, data=None),
            DebugStep(message="Second step", timestamp=start_time + 0.25, data={"key": "value"}),
            DebugStep(message="Final step", timestamp=start_time + 0.5, data=None),
        ]

    def test_init(self):
        """Test MatchingDebugInfo initialization."""
        steps = self.create_debug_steps()
        debug_info = MatchingDebugInfo(steps=steps, start_time=1000.0)

        assert debug_info.steps == steps
        assert debug_info.start_time == 1000.0

    def test_to_strings_empty(self):
        """Test to_strings with empty steps."""
        debug_info = MatchingDebugInfo(steps=[], start_time=1000.0)

        result = debug_info.to_strings()

        assert result == []

    def test_to_strings_single_step(self):
        """Test to_strings with single step."""
        steps = [DebugStep(message="Only step", timestamp=1000.1, data=None)]
        debug_info = MatchingDebugInfo(steps=steps, start_time=1000.0)

        result = debug_info.to_strings()

        assert len(result) == 1
        assert "100ms +100ms" in result[0]
        assert "Only step" in result[0]

    def test_to_strings_multiple_steps(self):
        """Test to_strings with multiple steps."""
        steps = self.create_debug_steps(1000.0)
        debug_info = MatchingDebugInfo(steps=steps, start_time=1000.0)

        result = debug_info.to_strings()

        assert len(result) == 3

        # First step: 100ms total, +100ms step
        assert "[100ms +100ms] First step" == result[0]

        # Second step: 250ms total, +150ms step (250-100)
        assert "[250ms +150ms] Second step" == result[1]

        # Third step: 500ms total, +250ms step (500-250)
        assert "[500ms +250ms] Final step" == result[2]

    def test_to_strings_timing_precision(self):
        """Test to_strings timing calculations with different precision."""
        steps = [
            DebugStep(message="Step 1", timestamp=1000.0567, data=None),
            DebugStep(message="Step 2", timestamp=1000.1234, data=None),
        ]
        debug_info = MatchingDebugInfo(steps=steps, start_time=1000.0)

        result = debug_info.to_strings()

        # Should round to nearest millisecond
        assert "[57ms +57ms] Step 1" == result[0]
        assert "[123ms +67ms] Step 2" == result[1]

    def test_summary_empty(self):
        """Test summary with empty steps."""
        debug_info = MatchingDebugInfo(steps=[], start_time=1000.0)

        summary = debug_info.summary

        expected = {"total_time_ms": 0, "step_count": 0}
        assert summary == expected

    def test_summary_with_steps(self):
        """Test summary with steps."""
        steps = self.create_debug_steps(1000.0)
        debug_info = MatchingDebugInfo(steps=steps, start_time=1000.0)

        summary = debug_info.summary

        assert summary["total_time_ms"] == 500.0  # Last timestamp - start_time
        assert summary["step_count"] == 3
        assert summary["steps"] == ["First step", "Second step", "Final step"]

    def test_summary_timing_calculation(self):
        """Test summary timing calculation accuracy."""
        steps = [
            DebugStep(message="Only step", timestamp=1000.123, data=None)
        ]
        debug_info = MatchingDebugInfo(steps=steps, start_time=1000.0)

        summary = debug_info.summary

        assert abs(summary["total_time_ms"] - 123.0) < 0.001  # Allow for floating point precision
        assert summary["step_count"] == 1
        assert summary["steps"] == ["Only step"]

    def test_summary_multiple_steps_timing(self):
        """Test summary with multiple steps timing."""
        start_time = 1000.0
        steps = [
            DebugStep(message="Step 1", timestamp=start_time + 0.05, data=None),
            DebugStep(message="Step 2", timestamp=start_time + 0.15, data=None),
            DebugStep(message="Step 3", timestamp=start_time + 0.3, data=None),
        ]
        debug_info = MatchingDebugInfo(steps=steps, start_time=start_time)

        summary = debug_info.summary

        assert abs(summary["total_time_ms"] - 300.0) < 0.001  # Allow for floating point precision
        assert summary["step_count"] == 3

    def test_summary_data_structure(self):
        """Test that summary contains all expected keys."""
        steps = self.create_debug_steps()
        debug_info = MatchingDebugInfo(steps=steps, start_time=1000.0)

        summary = debug_info.summary

        assert "total_time_ms" in summary
        assert "step_count" in summary
        assert "steps" in summary
        assert isinstance(summary["total_time_ms"], (int, float))
        assert isinstance(summary["step_count"], int)
        assert isinstance(summary["steps"], list)

    def test_property_access(self):
        """Test that summary is accessible as property."""
        debug_info = MatchingDebugInfo(steps=[], start_time=1000.0)

        # Should be accessible as property, not method
        summary1 = debug_info.summary
        summary2 = debug_info.summary

        assert summary1 == summary2
        assert isinstance(summary1, dict)


class TestDebugIntegration:
    """Integration tests for debug components."""

    def test_tracker_to_debug_info_integration(self):
        """Test full integration from tracker to debug info."""
        tracker = DebugStepTracker()

        # Add some steps
        tracker.add("Starting process")
        time.sleep(0.01)  # Small delay to ensure different timestamps
        tracker.add("Middle process", {"data": "test"})
        time.sleep(0.01)
        tracker.add("Ending process")

        # Convert to debug info
        debug_info = tracker.to_matching_debug_info()

        # Verify structure
        assert len(debug_info.steps) == 3
        assert debug_info.start_time == tracker.start_time

        # Verify string conversion works
        strings = debug_info.to_strings()
        assert len(strings) == 3
        assert all("ms" in s for s in strings)

        # Verify summary works
        summary = debug_info.summary
        assert summary["step_count"] == 3
        assert summary["total_time_ms"] > 0

    def test_empty_tracker_integration(self):
        """Test integration with empty tracker."""
        tracker = DebugStepTracker()
        debug_info = tracker.to_matching_debug_info()

        assert debug_info.steps == []
        assert debug_info.to_strings() == []
        assert debug_info.summary["step_count"] == 0
