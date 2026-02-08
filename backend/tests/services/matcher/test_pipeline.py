"""Test cases for the MatchingPipeline."""

import pytest
from unittest.mock import Mock, patch

from app.services.matcher.pipeline import MatchingPipeline
from app.services.matcher.context import MatchingContext, MatchingResult


class TestMatchingPipeline:
    """Test cases for MatchingPipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline = MatchingPipeline()
        self.mock_context = Mock(spec=MatchingContext)
        self.mock_context.debug = Mock()
        self.mock_context.debug.add = Mock()

    @patch('app.services.matcher.pipeline.SemanticMatchingStrategy')
    @patch('app.services.matcher.pipeline.FuzzyMatchingStrategy')
    def test_init(self, mock_fuzzy, mock_semantic):
        """Test pipeline initialization."""
        pipeline = MatchingPipeline()
        assert len(pipeline.strategies) == 2
        mock_semantic.assert_called()
        mock_fuzzy.assert_called()

    def test_execute_first_strategy_success(self):
        """Test pipeline stops after first successful strategy."""
        # Mock strategies
        strategy1 = Mock()
        strategy1.get_name.return_value = "Strategy1"
        result1 = MatchingResult(success=True, matches=[("p1", 1.0)], strategy_name="Strategy1")
        strategy1.match.return_value = result1

        strategy2 = Mock()
        strategy2.get_name.return_value = "Strategy2"

        self.pipeline.strategies = [strategy1, strategy2]

        # Execute
        success, result = self.pipeline.execute(self.mock_context, semantic_threshold=0.8, fuzzy_threshold=0.6)

        # Verify
        assert success is True
        assert result == result1
        assert result.success is True
        strategy1.match.assert_called_once()
        strategy2.match.assert_not_called()
        
        # Verify debug calls
        assert self.mock_context.debug.add.call_count >= 1

    def test_execute_fall_through_to_second_strategy(self):
        """Test pipeline continues to second strategy if first fails."""
        # Mock strategies
        strategy1 = Mock()
        strategy1.get_name.return_value = "Strategy1"
        result1 = MatchingResult(success=False, matches=[], strategy_name="Strategy1")
        strategy1.match.return_value = result1

        strategy2 = Mock()
        strategy2.get_name.return_value = "Fuzzy" # Use "Fuzzy" to test default threshold mapping
        result2 = MatchingResult(success=True, matches=[("p2", 0.9)], strategy_name="Fuzzy")
        strategy2.match.return_value = result2

        self.pipeline.strategies = [strategy1, strategy2]

        # Execute
        success, result = self.pipeline.execute(self.mock_context, semantic_threshold=0.8, fuzzy_threshold=0.6)

        # Verify
        assert success is True
        assert result == result2
        strategy1.match.assert_called_once()
        strategy2.match.assert_called_once()
        
        # Check threshold passed to strategy 2 (Fuzzy)
        # It should use fuzzy_threshold (0.6)
        strategy2.match.assert_called_with(self.mock_context, 0.6, 10)

    def test_execute_all_fail(self):
        """Test pipeline when all strategies fail."""
        # Mock strategies
        strategy1 = Mock()
        strategy1.get_name.return_value = "Strategy1"
        result1 = MatchingResult(success=False, matches=[], strategy_name="Strategy1")
        strategy1.match.return_value = result1

        strategy2 = Mock()
        strategy2.get_name.return_value = "Strategy2"
        result2 = MatchingResult(success=False, matches=[], strategy_name="Strategy2")
        strategy2.match.return_value = result2

        self.pipeline.strategies = [strategy1, strategy2]

        # Execute
        success, result = self.pipeline.execute(self.mock_context)

        # Verify
        assert success is False
        assert result == result2
        assert len(result.matches) == 0
        strategy1.match.assert_called_once()
        strategy2.match.assert_called_once()

    def test_execute_thresholds_mapping(self):
        """Test that correct thresholds are passed to strategies."""
        # Mock strategies
        strategy1 = Mock()
        strategy1.get_name.return_value = "Semantic"
        result1 = MatchingResult(success=False, matches=[], strategy_name="Semantic")
        strategy1.match.return_value = result1

        strategy2 = Mock()
        strategy2.get_name.return_value = "Fuzzy"
        result2 = MatchingResult(success=False, matches=[], strategy_name="Fuzzy")
        strategy2.match.return_value = result2

        self.pipeline.strategies = [strategy1, strategy2]

        # Execute
        self.pipeline.execute(
            self.mock_context, 
            semantic_threshold=0.85, 
            fuzzy_threshold=0.65,
            max_candidates=5
        )

        # Verify Semantic strategy got semantic_threshold
        strategy1.match.assert_called_with(self.mock_context, 0.85, 5)
        
        # Verify Fuzzy strategy got fuzzy_threshold
        strategy2.match.assert_called_with(self.mock_context, 0.65, 5)

    def test_execute_metrics_logging(self):
        """Test that strategy execution metrics are logged to debug."""
        # Mock strategies
        strategy1 = Mock()
        strategy1.get_name.return_value = "Strategy1"
        result1 = MatchingResult(
            success=True, 
            matches=[("p1", 1.0)], 
            strategy_name="Strategy1",
            candidates_checked=10,
            processing_time_ms=50.0
        )
        strategy1.match.return_value = result1
        self.pipeline.strategies = [strategy1]

        # Execute
        self.pipeline.execute(self.mock_context)

        # Verify debug logs contain metrics
        debug_calls = [str(call) for call in self.mock_context.debug.add.call_args_list]
        metrics_log = next((log for log in debug_calls if "processing_time" in log), None)
        assert metrics_log is not None
        assert "50.00ms" in metrics_log
        assert "candidates_checked=10" in metrics_log

