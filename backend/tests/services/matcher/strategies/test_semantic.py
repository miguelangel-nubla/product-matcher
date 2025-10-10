"""Test cases for the Semantic matching strategy."""

import pytest
from unittest.mock import Mock, patch

from app.services.matcher.strategies.semantic import SemanticMatchingStrategy
from app.services.matcher.context import MatchingContext, MatchingResult


class TestSemanticMatchingStrategy:
    """Test cases for SemanticMatchingStrategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = SemanticMatchingStrategy()
        self.mock_debug = Mock()
        self.mock_debug.add = Mock()

    def create_context(self, input_tokens, normalized_aliases, language="en"):
        """Create a MatchingContext for testing."""
        mock_backend = Mock()
        mock_backend.language = language
        return MatchingContext(
            input_tokens=input_tokens,
            normalized_input=" ".join(input_tokens),
            normalized_aliases=normalized_aliases,
            backend=mock_backend,
            debug=self.mock_debug
        )

    def test_get_name(self):
        """Test strategy name."""
        assert self.strategy.get_name() == "Semantic"

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_with_semantic_matches(self, mock_get_utils):
        """Test semantic matching with matches above threshold."""
        # Mock the matching utils
        mock_utils = Mock()
        mock_utils.calculate_semantic_similarity.side_effect = [0.9, 0.7, 0.3]
        mock_get_utils.return_value = mock_utils

        input_tokens = ["apple", "juice"]
        normalized_aliases = [
            ("product1", "Apple Juice", ["apple", "juice"]),
            ("product2", "Fruit Drink", ["fruit", "drink"]),
            ("product3", "Water", ["water"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.6, max_candidates=5)

        assert isinstance(result, MatchingResult)
        assert result.success is True
        assert result.strategy_name == "Semantic"
        assert result.candidates_checked == 3
        assert result.threshold_used == 0.6

        # Should return 2 matches above threshold (0.9 and 0.7)
        assert len(result.matches) == 2
        assert result.matches[0] == ("product1", 0.9)  # Highest score first
        assert result.matches[1] == ("product2", 0.7)

        # Verify the matching utils was called correctly
        mock_get_utils.assert_called_once_with("en")
        assert mock_utils.calculate_semantic_similarity.call_count == 3

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_no_matches_above_threshold(self, mock_get_utils):
        """Test semantic matching when no matches meet threshold."""
        mock_utils = Mock()
        mock_utils.calculate_semantic_similarity.side_effect = [0.3, 0.2, 0.1]
        mock_get_utils.return_value = mock_utils

        input_tokens = ["apple", "juice"]
        normalized_aliases = [
            ("product1", "Chocolate Bar", ["chocolate", "bar"]),
            ("product2", "Water Bottle", ["water", "bottle"]),
            ("product3", "Bread Loaf", ["bread", "loaf"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)

        assert result.success is False
        assert len(result.matches) == 0
        assert result.candidates_checked == 3

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_with_max_candidates_limit(self, mock_get_utils):
        """Test that semantic matching respects max_candidates limit."""
        mock_utils = Mock()
        # Return high scores for all products
        mock_utils.calculate_semantic_similarity.return_value = 0.9
        mock_get_utils.return_value = mock_utils

        input_tokens = ["apple"]
        normalized_aliases = [
            (f"product{i}", f"Apple Product {i}", ["apple", "product", str(i)])
            for i in range(10)
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.8, max_candidates=3)

        assert result.success is True
        assert len(result.matches) == 3  # Limited by max_candidates
        assert result.candidates_checked == 10

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_best_score_per_product(self, mock_get_utils):
        """Test that only the best score per product is tracked."""
        mock_utils = Mock()
        mock_utils.calculate_semantic_similarity.side_effect = [0.8, 0.9, 0.7]  # product1 gets 0.8 then 0.9
        mock_get_utils.return_value = mock_utils

        input_tokens = ["apple"]
        normalized_aliases = [
            ("product1", "Apple", ["apple"]),
            ("product1", "Green Apple", ["green", "apple"]),  # Same product, better score
            ("product2", "Apple Pie", ["apple", "pie"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.6, max_candidates=5)

        assert result.success is True
        assert len(result.matches) == 2  # Only 2 unique products

        # product1 should have the better score (0.9)
        product1_match = next(m for m in result.matches if m[0] == "product1")
        assert product1_match[1] == 0.9

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_empty_input(self, mock_get_utils):
        """Test semantic matching with empty input."""
        mock_utils = Mock()
        mock_utils.calculate_semantic_similarity.return_value = 0.0
        mock_get_utils.return_value = mock_utils

        input_tokens = []
        normalized_aliases = [
            ("product1", "Apple Juice", ["apple", "juice"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.5, max_candidates=5)

        assert result.success is False
        assert len(result.matches) == 0

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_empty_aliases(self, mock_get_utils):
        """Test semantic matching with no aliases."""
        mock_utils = Mock()
        mock_get_utils.return_value = mock_utils

        input_tokens = ["apple", "juice"]
        normalized_aliases = []

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.5, max_candidates=5)

        assert result.success is False
        assert len(result.matches) == 0
        assert result.candidates_checked == 0

        # Should not call semantic similarity with no aliases
        mock_utils.calculate_semantic_similarity.assert_not_called()

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_different_language(self, mock_get_utils):
        """Test semantic matching with different language."""
        mock_utils = Mock()
        mock_utils.calculate_semantic_similarity.return_value = 0.8
        mock_get_utils.return_value = mock_utils

        input_tokens = ["manzana"]  # Spanish for apple
        normalized_aliases = [
            ("product1", "Manzana", ["manzana"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases, language="es")
        result = self.strategy.match(context, threshold=0.7, max_candidates=5)

        assert result.success is True
        mock_get_utils.assert_called_once_with("es")

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_debug_tracking(self, mock_get_utils):
        """Test that debug information is properly tracked."""
        mock_utils = Mock()
        mock_utils.calculate_semantic_similarity.return_value = 0.8
        mock_get_utils.return_value = mock_utils

        input_tokens = ["apple"]
        normalized_aliases = [
            ("product1", "Apple", ["apple"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.7, max_candidates=5)

        # Verify debug calls were made
        assert self.mock_debug.add.call_count >= 3

        # Check that some debug calls contain expected information
        debug_calls = [call[0][0] for call in self.mock_debug.add.call_args_list]
        assert any("Starting SpaCy semantic matching" in call for call in debug_calls)
        assert any("semantic similarity calculation" in call.lower() for call in debug_calls)

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_scores_sorted_descending(self, mock_get_utils):
        """Test that matches are sorted by score in descending order."""
        mock_utils = Mock()
        mock_utils.calculate_semantic_similarity.side_effect = [0.7, 0.9, 0.8]
        mock_get_utils.return_value = mock_utils

        input_tokens = ["apple"]
        normalized_aliases = [
            ("product1", "Apple Red", ["apple", "red"]),
            ("product2", "Apple Green", ["apple", "green"]),
            ("product3", "Apple Yellow", ["apple", "yellow"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.6, max_candidates=5)

        assert result.success is True
        assert len(result.matches) == 3

        # Should be sorted by score descending: 0.9, 0.8, 0.7
        assert result.matches[0] == ("product2", 0.9)
        assert result.matches[1] == ("product3", 0.8)
        assert result.matches[2] == ("product1", 0.7)

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_processing_time_tracked(self, mock_get_utils):
        """Test that processing time is tracked."""
        mock_utils = Mock()
        mock_utils.calculate_semantic_similarity.return_value = 0.8
        mock_get_utils.return_value = mock_utils

        input_tokens = ["apple"]
        normalized_aliases = [
            ("product1", "Apple", ["apple"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.7, max_candidates=5)

        assert hasattr(result, 'processing_time_ms')
        assert result.processing_time_ms >= 0

    @patch('app.services.matching.utils.registry.get_matching_utils')
    def test_match_debug_includes_all_scores(self, mock_get_utils):
        """Test that debug includes all score calculations."""
        mock_utils = Mock()
        mock_utils.calculate_semantic_similarity.side_effect = [0.9, 0.3]
        mock_get_utils.return_value = mock_utils

        input_tokens = ["apple"]
        normalized_aliases = [
            ("product1", "Apple", ["apple"]),
            ("product2", "Water", ["water"]),
        ]

        context = self.create_context(input_tokens, normalized_aliases)
        result = self.strategy.match(context, threshold=0.8, max_candidates=5)

        # Find the debug call that includes the detailed scores
        debug_calls_with_data = [
            call for call in self.mock_debug.add.call_args_list
            if len(call[0]) > 1 and isinstance(call[0][1], list)
        ]

        assert len(debug_calls_with_data) >= 1

        # Check that the scores data includes both products
        scores_data = debug_calls_with_data[0][0][1]
        assert len(scores_data) == 2

        # Verify the score data structure
        assert all('product_id' in item for item in scores_data)
        assert all('score' in item for item in scores_data)
        assert all('above_threshold' in item for item in scores_data)
