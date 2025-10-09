"""Test cases for the ProductMatcher core service."""

import pytest
from unittest.mock import Mock, patch

from app.services.matcher.matcher import ProductMatcher
from app.models import BackendConfig, AdapterConfig
from app.services.debug import DebugStepTracker


class TestProductMatcher:
    """Test cases for ProductMatcher."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = ProductMatcher()
        self.backend_config = BackendConfig(
            description="Test backend",
            language="en",
            adapter=AdapterConfig(type="mock", config={})
        )

    def test_init(self):
        """Test ProductMatcher initialization."""
        assert self.matcher.data_preparation is not None
        assert self.matcher.pipeline is not None

    @patch('app.services.normalization.registry.get_normalizer')
    def test_get_normalizer_success(self, mock_get_normalizer):
        """Test successful normalizer retrieval."""
        mock_normalizer = Mock()
        mock_get_normalizer.return_value = mock_normalizer

        result = self.matcher._get_normalizer("en")

        assert result == mock_normalizer
        mock_get_normalizer.assert_called_once_with("en")

    @patch('app.services.normalization.registry.get_normalizer')
    def test_get_normalizer_error(self, mock_get_normalizer):
        """Test normalizer retrieval error."""
        mock_get_normalizer.side_effect = ValueError("Unsupported language")

        with pytest.raises(ValueError, match="Unsupported language"):
            self.matcher._get_normalizer("invalid")

    @patch('app.services.matcher.matcher.ProductMatcher._get_normalizer')
    def test_match_product_success(self, mock_get_normalizer):
        """Test successful product matching."""
        # Mock normalizer
        mock_normalizer = Mock()
        mock_get_normalizer.return_value = mock_normalizer

        # Mock data preparation
        mock_context = Mock()
        mock_context.normalized_input = "normalized apple juice"
        self.matcher.data_preparation.prepare_context = Mock(return_value=mock_context)

        # Mock pipeline execution
        mock_result = Mock()
        mock_result.strategy_name = "Fuzzy"
        mock_result.matches = [("product1", 0.9), ("product2", 0.8)]
        self.matcher.pipeline.execute = Mock(return_value=(True, mock_result))

        # Execute
        success, normalized_input, matches, debug_info = self.matcher.match_product(
            input_query="apple juice",
            backend_config=self.backend_config,
            threshold=0.8,
            max_candidates=5
        )

        # Verify
        assert success is True
        assert normalized_input == "normalized apple juice"
        assert matches == [("product1", 0.9), ("product2", 0.8)]
        assert isinstance(debug_info, list)

        # Verify method calls
        mock_get_normalizer.assert_called_once_with("en")
        self.matcher.data_preparation.prepare_context.assert_called_once()
        self.matcher.pipeline.execute.assert_called_once_with(
            context=mock_context,
            semantic_threshold=0.8,
            fuzzy_threshold=0.8,
            max_candidates=5
        )

    @patch('app.services.matcher.matcher.ProductMatcher._get_normalizer')
    def test_match_product_with_debug_tracker(self, mock_get_normalizer):
        """Test product matching with provided debug tracker."""
        mock_normalizer = Mock()
        mock_get_normalizer.return_value = mock_normalizer

        mock_context = Mock()
        mock_context.normalized_input = "normalized text"
        self.matcher.data_preparation.prepare_context = Mock(return_value=mock_context)

        mock_result = Mock()
        mock_result.strategy_name = "Semantic"
        mock_result.matches = []
        self.matcher.pipeline.execute = Mock(return_value=(False, mock_result))

        # Provide debug tracker
        debug_tracker = DebugStepTracker()

        # Execute
        success, normalized_input, matches, debug_info = self.matcher.match_product(
            input_query="test query",
            backend_config=self.backend_config,
            debug=debug_tracker
        )

        # Verify
        assert success is False
        assert len(debug_info) > 0  # Should have debug steps

    @patch('app.services.matcher.matcher.ProductMatcher._get_normalizer')
    def test_match_product_normalizer_error(self, mock_get_normalizer):
        """Test product matching when normalizer fails."""
        mock_get_normalizer.side_effect = Exception("Normalizer error")

        # Execute
        success, normalized_input, matches, debug_info = self.matcher.match_product(
            input_query="apple juice",
            backend_config=self.backend_config
        )

        # Verify error handling
        assert success is False
        assert normalized_input == "apple juice"  # Should return original input
        assert matches == []
        assert len(debug_info) > 0  # Should have error debug info

    @patch('app.services.matcher.matcher.ProductMatcher._get_normalizer')
    def test_match_product_data_preparation_error(self, mock_get_normalizer):
        """Test product matching when data preparation fails."""
        mock_normalizer = Mock()
        mock_get_normalizer.return_value = mock_normalizer

        self.matcher.data_preparation.prepare_context = Mock(
            side_effect=Exception("Data preparation error")
        )

        # Execute
        success, normalized_input, matches, debug_info = self.matcher.match_product(
            input_query="apple juice",
            backend_config=self.backend_config
        )

        # Verify error handling
        assert success is False
        assert normalized_input == "apple juice"
        assert matches == []
        assert len(debug_info) > 0

    @patch('app.services.matcher.matcher.ProductMatcher._get_normalizer')
    def test_match_product_pipeline_error(self, mock_get_normalizer):
        """Test product matching when pipeline execution fails."""
        mock_normalizer = Mock()
        mock_get_normalizer.return_value = mock_normalizer

        mock_context = Mock()
        self.matcher.data_preparation.prepare_context = Mock(return_value=mock_context)

        self.matcher.pipeline.execute = Mock(
            side_effect=Exception("Pipeline error")
        )

        # Execute
        success, normalized_input, matches, debug_info = self.matcher.match_product(
            input_query="apple juice",
            backend_config=self.backend_config
        )

        # Verify error handling
        assert success is False
        assert normalized_input == "apple juice"
        assert matches == []
        assert len(debug_info) > 0

    @patch('app.services.matcher.matcher.ProductMatcher._get_normalizer')
    def test_match_product_different_thresholds(self, mock_get_normalizer):
        """Test product matching with different threshold values."""
        mock_normalizer = Mock()
        mock_get_normalizer.return_value = mock_normalizer

        mock_context = Mock()
        mock_context.normalized_input = "normalized text"
        self.matcher.data_preparation.prepare_context = Mock(return_value=mock_context)

        mock_result = Mock()
        mock_result.strategy_name = "Fuzzy"
        mock_result.matches = []
        self.matcher.pipeline.execute = Mock(return_value=(False, mock_result))

        # Test with custom threshold
        self.matcher.match_product(
            input_query="test",
            backend_config=self.backend_config,
            threshold=0.9,
            max_candidates=3
        )

        # Verify threshold passed to pipeline
        self.matcher.pipeline.execute.assert_called_once_with(
            context=mock_context,
            semantic_threshold=0.9,
            fuzzy_threshold=0.9,
            max_candidates=3
        )

    @patch('app.adapters.registry.get_backend')
    def test_add_learned_alias_success(self, mock_get_backend):
        """Test successful alias addition."""
        mock_backend = Mock()
        mock_backend.add_alias.return_value = True
        mock_get_backend.return_value = mock_backend

        # Execute
        success, error = self.matcher.add_learned_alias("product123", "new alias")

        # Verify
        assert success is True
        assert error is None
        mock_get_backend.assert_called_once_with("grocy")
        mock_backend.add_alias.assert_called_once_with("product123", "new alias")

    @patch('app.adapters.registry.get_backend')
    def test_add_learned_alias_backend_failure(self, mock_get_backend):
        """Test alias addition when backend fails."""
        mock_backend = Mock()
        mock_backend.add_alias.return_value = False
        mock_get_backend.return_value = mock_backend

        # Execute
        success, error = self.matcher.add_learned_alias("product123", "new alias")

        # Verify
        assert success is False
        assert "Backend failed to add alias" in error

    @patch('app.adapters.registry.get_backend')
    def test_add_learned_alias_no_add_alias_method(self, mock_get_backend):
        """Test alias addition when backend doesn't support add_alias."""
        mock_backend = Mock()
        del mock_backend.add_alias  # Remove the method
        mock_get_backend.return_value = mock_backend

        # Execute
        success, error = self.matcher.add_learned_alias("product123", "new alias")

        # Verify
        assert success is False
        assert "Backend does not support adding aliases" in error

    @patch('app.adapters.registry.get_backend')
    def test_add_learned_alias_backend_error(self, mock_get_backend):
        """Test alias addition when backend raises error."""
        mock_get_backend.side_effect = Exception("Backend connection error")

        # Execute
        success, error = self.matcher.add_learned_alias("product123", "new alias")

        # Verify
        assert success is False
        assert "Error adding learned alias" in error
        assert "Backend connection error" in error

    @patch('app.adapters.registry.get_backend')
    def test_add_learned_alias_add_alias_exception(self, mock_get_backend):
        """Test alias addition when add_alias method raises exception."""
        mock_backend = Mock()
        mock_backend.add_alias.side_effect = Exception("Add alias error")
        mock_get_backend.return_value = mock_backend

        # Execute
        success, error = self.matcher.add_learned_alias("product123", "new alias")

        # Verify
        assert success is False
        assert "Error adding learned alias" in error
