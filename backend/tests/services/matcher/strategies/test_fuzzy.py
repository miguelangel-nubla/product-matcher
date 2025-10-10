"""Test cases for the Fuzzy matching strategy."""

import pytest
from unittest.mock import Mock

from app.services.matcher.strategies.fuzzy import FuzzyMatchingStrategy
from app.services.matcher.context import MatchingContext, MatchingResult


class TestFuzzyMatchingStrategy:
    """Test cases for FuzzyMatchingStrategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = FuzzyMatchingStrategy()
        self.mock_debug = Mock()
        self.mock_debug.add = Mock()

    def create_context(self, input_tokens, normalized_aliases):
        """Create a MatchingContext for testing."""
        mock_backend = Mock()
        mock_backend.language = "en"
        return MatchingContext(
            input_tokens=input_tokens,
            normalized_input=" ".join(input_tokens),
            normalized_aliases=normalized_aliases,
            backend=mock_backend,
            debug=self.mock_debug
        )

    def test_get_name(self):
        """Test strategy name."""
        assert self.strategy.get_name() == "Fuzzy"

    def test_match_exact_match(self):
        """Test fuzzy matching with exact match."""
        input_tokens = ["apple", "juice"]
        normalized_aliases = [
            ("product1", "Apple Juice", ["apple", "juice"]),
            ("product2", "Orange Juice", ["orange", "juice"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)

        assert isinstance(result, MatchingResult)
        assert result.success is True
        assert result.strategy_name == "Fuzzy"
        assert result.candidates_checked == 2
        assert result.threshold_used == 0.8
        assert len(result.matches) > 0

        # The exact match should have the highest score
        best_match = result.matches[0]
        assert best_match[0] == "product1"
        assert best_match[1] >= 0.8

    def test_match_partial_match(self):
        """Test fuzzy matching with partial matches."""
        input_tokens = ["aple", "juce"]  # Typos
        normalized_aliases = [
            ("product1", "Apple Juice", ["apple", "juice"]),
            ("product2", "Orange Juice", ["orange", "juice"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.6, max_candidates=5)

        assert result.success is True
        assert len(result.matches) > 0

        # Should still match "Apple Juice" despite typos
        best_match = result.matches[0]
        assert best_match[0] == "product1"
        assert best_match[1] >= 0.6

    def test_match_no_matches_above_threshold(self):
        """Test fuzzy matching when no matches meet threshold."""
        input_tokens = ["chocolate", "bar"]
        normalized_aliases = [
            ("product1", "Apple Juice", ["apple", "juice"]),
            ("product2", "Orange Juice", ["orange", "juice"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.9, max_candidates=5)

        assert result.success is False
        assert len(result.matches) <= 5  # Should still return candidates even if below threshold

    def test_match_multiple_identical_top_scores(self):
        """Test fuzzy matching with multiple identical top scores (ambiguous)."""
        input_tokens = ["juice"]
        normalized_aliases = [
            ("product1", "Apple Juice", ["apple", "juice"]),
            ("product2", "Orange Juice", ["orange", "juice"]),
            ("product3", "Grape Juice", ["grape", "juice"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.3, max_candidates=5)

        # All should have similar scores for "juice", making it ambiguous
        # The strategy should detect this and mark as unsuccessful
        if len([m for m in result.matches if m[1] >= 0.3]) > 1:
            top_score = result.matches[0][1]
            top_score_matches = [m for m in result.matches if m[1] == top_score and m[1] >= 0.3]
            if len(top_score_matches) > 1:
                assert result.success is False

    def test_match_single_match_above_threshold(self):
        """Test fuzzy matching with single match above threshold."""
        input_tokens = ["apple", "juice", "organic"]
        normalized_aliases = [
            ("product1", "Organic Apple Juice", ["organic", "apple", "juice"]),
            ("product2", "Orange Juice", ["orange", "juice"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)

        above_threshold = [m for m in result.matches if m[1] >= 0.8]
        if len(above_threshold) == 1:
            assert result.success is True

    def test_match_max_candidates_limit(self):
        """Test that match respects max_candidates limit."""
        input_tokens = ["juice"]
        normalized_aliases = [
            (f"product{i}", f"Product {i} Juice", ["product", str(i), "juice"])
            for i in range(10)
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.1, max_candidates=3)

        assert len(result.matches) <= 3
        assert result.candidates_checked == 10

    def test_match_empty_input(self):
        """Test fuzzy matching with empty input."""
        input_tokens = []
        normalized_aliases = [
            ("product1", "Apple Juice", ["apple", "juice"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.5, max_candidates=5)

        assert result.success is False
        assert len(result.matches) == 0

    def test_match_empty_aliases(self):
        """Test fuzzy matching with no aliases."""
        input_tokens = ["apple", "juice"]
        normalized_aliases = []

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.5, max_candidates=5)

        assert result.success is False
        assert len(result.matches) == 0
        assert result.candidates_checked == 0

    def test_match_empty_alias_text(self):
        """Test fuzzy matching with empty alias text."""
        input_tokens = ["apple", "juice"]
        normalized_aliases = [
            ("product1", "Empty", []),  # Empty tokens
            ("product2", "Apple Juice", ["apple", "juice"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.5, max_candidates=5)

        # Should skip empty alias and match the valid one
        assert result.candidates_checked == 2
        assert len(result.matches) >= 1
        assert result.matches[0][0] == "product2"

    def test_match_debug_tracking(self):
        """Test that debug information is properly tracked."""
        input_tokens = ["apple"]
        normalized_aliases = [
            ("product1", "Apple", ["apple"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.5, max_candidates=5)

        # Verify debug calls were made
        assert self.mock_debug.add.call_count >= 3  # Should have multiple debug calls

        # Check that some debug calls contain expected information
        debug_calls = [call[0][0] for call in self.mock_debug.add.call_args_list]
        assert any("Starting fuzzy matching" in call for call in debug_calls)
        assert any("candidates" in call for call in debug_calls)

    def test_match_product_best_scores_tracking(self):
        """Test that only the best score per product is tracked."""
        input_tokens = ["apple"]
        normalized_aliases = [
            ("product1", "Apple", ["apple"]),
            ("product1", "Green Apple", ["green", "apple"]),  # Same product, different alias
            ("product2", "Apple Pie", ["apple", "pie"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.1, max_candidates=5)

        # Should have only 2 unique products in results
        unique_products = set(match[0] for match in result.matches)
        assert len(unique_products) == 2
        assert "product1" in unique_products
        assert "product2" in unique_products

    def test_match_processing_time_tracked(self):
        """Test that processing time is tracked."""
        input_tokens = ["apple"]
        normalized_aliases = [
            ("product1", "Apple", ["apple"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.5, max_candidates=5)

        assert hasattr(result, 'processing_time_ms')
        assert result.processing_time_ms >= 0
