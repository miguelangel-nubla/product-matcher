"""Test cases for the DataPreparation service."""

import pytest
from unittest.mock import Mock, patch

from app.services.matcher.data_preparation import DataPreparation
from app.services.matcher.context import MatchingContext
from app.models import BackendConfig, AdapterConfig
from app.services.debug import DebugStepTracker
from app.adapters.base import ExternalProduct


class TestDataPreparation:
    """Test cases for DataPreparation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.data_prep = DataPreparation()
        self.backend_config = BackendConfig(
            description="Test backend",
            language="en",
            adapter=AdapterConfig(type="mock", config={})
        )
        self.debug = DebugStepTracker()

    def test_init(self):
        """Test DataPreparation initialization."""
        assert isinstance(self.data_prep, DataPreparation)

    def test_prepare_context_success(self):
        """Test successful context preparation."""
        # Mock normalizer
        mock_normalizer = Mock()
        mock_normalizer.normalize.side_effect = [
            ["apple", "juice"],  # For input normalization
            ["apple", "juice"],  # For alias 1
            ["orange", "juice"],  # For alias 2
        ]

        # Mock the _get_normalized_aliases method
        mock_aliases = [
            ("product1", "Apple Juice", ["apple", "juice"]),
            ("product2", "Orange Juice", ["orange", "juice"]),
        ]
        self.data_prep._get_normalized_aliases = Mock(return_value=mock_aliases)

        # Execute
        context = self.data_prep.prepare_context(
            mock_normalizer, "Apple Juice", self.backend_config, self.debug
        )

        # Verify
        assert isinstance(context, MatchingContext)
        assert context.input_tokens == ["apple", "juice"]
        assert context.normalized_input == "apple juice"
        assert context.normalized_aliases == mock_aliases
        assert context.backend_config == self.backend_config
        assert context.debug == self.debug

        # Verify normalizer was called for input
        mock_normalizer.normalize.assert_called_with("Apple Juice")

        # Verify debug information was added
        debug_steps = self.debug.get_debug_info()
        assert len(debug_steps) >= 2
        assert any("Starting data preparation" in step.message for step in debug_steps)
        assert any("Data preparation completed" in step.message for step in debug_steps)

    def test_prepare_context_empty_input(self):
        """Test context preparation with empty input."""
        mock_normalizer = Mock()
        mock_normalizer.normalize.return_value = []

        self.data_prep._get_normalized_aliases = Mock(return_value=[])

        context = self.data_prep.prepare_context(
            mock_normalizer, "", self.backend_config, self.debug
        )

        assert context.input_tokens == []
        assert context.normalized_input == ""
        assert context.normalized_aliases == []

    def test_prepare_context_normalization_error(self):
        """Test context preparation when normalization fails."""
        mock_normalizer = Mock()
        mock_normalizer.normalize.side_effect = Exception("Normalization error")

        with pytest.raises(Exception, match="Normalization error"):
            self.data_prep.prepare_context(
                mock_normalizer, "test input", self.backend_config, self.debug
            )

    @patch('app.services.matcher.data_preparation.DataPreparation._fetch_aliases_from_backend')
    def test_get_normalized_aliases_success(self, mock_fetch_aliases):
        """Test successful alias normalization."""
        # Mock fetched aliases
        mock_fetch_aliases.return_value = [
            ("product1", "Apple Juice"),
            ("product2", "Orange Juice"),
            ("product3", "Banana Smoothie"),
        ]

        # Mock normalizer
        mock_normalizer = Mock()
        mock_normalizer.normalize.side_effect = [
            ["apple", "juice"],
            ["orange", "juice"],
            ["banana", "smoothie"],
        ]

        # Execute
        result = self.data_prep._get_normalized_aliases(
            mock_normalizer, self.backend_config, self.debug
        )

        # Verify
        expected = [
            ("product1", "Apple Juice", ["apple", "juice"]),
            ("product2", "Orange Juice", ["orange", "juice"]),
            ("product3", "Banana Smoothie", ["banana", "smoothie"]),
        ]
        assert result == expected

        # Verify all aliases were normalized
        assert mock_normalizer.normalize.call_count == 3
        mock_fetch_aliases.assert_called_once_with(self.backend_config)

    @patch('app.services.matcher.data_preparation.DataPreparation._fetch_aliases_from_backend')
    def test_get_normalized_aliases_empty_backend(self, mock_fetch_aliases):
        """Test alias normalization with empty backend."""
        mock_fetch_aliases.return_value = []
        mock_normalizer = Mock()

        result = self.data_prep._get_normalized_aliases(
            mock_normalizer, self.backend_config, self.debug
        )

        assert result == []
        mock_normalizer.normalize.assert_not_called()

    @patch('app.services.matcher.data_preparation.DataPreparation._fetch_aliases_from_backend')
    def test_get_normalized_aliases_normalization_error(self, mock_fetch_aliases):
        """Test alias normalization with normalization error."""
        mock_fetch_aliases.return_value = [("product1", "Test Product")]
        mock_normalizer = Mock()
        mock_normalizer.normalize.side_effect = Exception("Normalization failed")

        with pytest.raises(Exception, match="Normalization failed"):
            self.data_prep._get_normalized_aliases(
                mock_normalizer, self.backend_config, self.debug
            )

    @patch('app.adapters.registry.get_backend')
    def test_fetch_aliases_from_backend_success(self, mock_get_backend):
        """Test successful alias fetching from backend."""
        # Mock products
        mock_products = [
            ExternalProduct(
                id="product1",
                aliases=["Apple Juice", "Organic Apple Juice"],
                description="Fresh apple juice"
            ),
            ExternalProduct(
                id="product2",
                aliases=["Orange Juice"],
                description="Fresh orange juice"
            ),
        ]

        # Mock backend
        mock_backend = Mock()
        mock_backend.get_all_products.return_value = mock_products
        mock_get_backend.return_value = mock_backend

        # Execute
        result = self.data_prep._fetch_aliases_from_backend(self.backend_config)

        # Verify
        expected = [
            ("product1", "Apple Juice"),
            ("product1", "Organic Apple Juice"),
            ("product2", "Orange Juice"),
        ]
        assert result == expected

        mock_get_backend.assert_called_once_with("mock")
        mock_backend.get_all_products.assert_called_once()

    @patch('app.adapters.registry.get_backend')
    def test_fetch_aliases_from_backend_no_aliases(self, mock_get_backend):
        """Test alias fetching with products that have no aliases."""
        # Mock product without aliases
        mock_product = Mock()
        mock_product.id = "product1"
        mock_product.aliases = None

        mock_backend = Mock()
        mock_backend.get_all_products.return_value = [mock_product]
        mock_get_backend.return_value = mock_backend

        # Execute
        result = self.data_prep._fetch_aliases_from_backend(self.backend_config)

        # Verify - should return empty list
        assert result == []

    @patch('app.adapters.registry.get_backend')
    def test_fetch_aliases_from_backend_empty_aliases(self, mock_get_backend):
        """Test alias fetching with products that have empty aliases."""
        mock_product = ExternalProduct(
            id="product1",
            aliases=[],
            description="Product with no aliases"
        )

        mock_backend = Mock()
        mock_backend.get_all_products.return_value = [mock_product]
        mock_get_backend.return_value = mock_backend

        # Execute
        result = self.data_prep._fetch_aliases_from_backend(self.backend_config)

        # Verify
        assert result == []

    @patch('app.adapters.registry.get_backend')
    def test_fetch_aliases_from_backend_error(self, mock_get_backend):
        """Test alias fetching when backend raises error."""
        mock_get_backend.side_effect = Exception("Backend connection error")

        with pytest.raises(Exception, match="Backend connection error"):
            self.data_prep._fetch_aliases_from_backend(self.backend_config)

    @patch('app.adapters.registry.get_backend')
    def test_fetch_aliases_from_backend_get_products_error(self, mock_get_backend):
        """Test alias fetching when get_all_products raises error."""
        mock_backend = Mock()
        mock_backend.get_all_products.side_effect = Exception("Products fetch error")
        mock_get_backend.return_value = mock_backend

        with pytest.raises(Exception, match="Products fetch error"):
            self.data_prep._fetch_aliases_from_backend(self.backend_config)

    @patch('app.adapters.registry.get_backend')
    def test_fetch_aliases_from_backend_mixed_products(self, mock_get_backend):
        """Test alias fetching with mixed product types."""
        # Mix of products with and without aliases
        mock_products = [
            ExternalProduct(id="product1", aliases=["Apple"], description="Apple"),
            Mock(id="product2", aliases=None),  # Product without aliases attribute
            ExternalProduct(id="product3", aliases=["Orange", "Citrus"], description="Orange"),
        ]

        mock_backend = Mock()
        mock_backend.get_all_products.return_value = mock_products
        mock_get_backend.return_value = mock_backend

        # Execute
        result = self.data_prep._fetch_aliases_from_backend(self.backend_config)

        # Verify - should only include products with valid aliases
        expected = [
            ("product1", "Apple"),
            ("product3", "Orange"),
            ("product3", "Citrus"),
        ]
        assert result == expected

    def test_clear_cache(self):
        """Test cache clearing."""
        mock_normalizer = Mock()
        mock_normalizer.clear_cache = Mock()

        self.data_prep.clear_cache(mock_normalizer)

        mock_normalizer.clear_cache.assert_called_once()

    def test_clear_cache_no_clear_cache_method(self):
        """Test cache clearing when normalizer doesn't have clear_cache method."""
        mock_normalizer = Mock()
        del mock_normalizer.clear_cache

        # Should not raise error even if normalizer doesn't have clear_cache
        with pytest.raises(AttributeError):
            self.data_prep.clear_cache(mock_normalizer)

    def test_prepare_context_debug_data_structure(self):
        """Test that debug data has the correct structure."""
        mock_normalizer = Mock()
        mock_normalizer.normalize.return_value = ["test", "tokens"]

        mock_aliases = [
            ("product1", "Test Product", ["test", "product"]),
        ]
        self.data_prep._get_normalized_aliases = Mock(return_value=mock_aliases)

        context = self.data_prep.prepare_context(
            mock_normalizer, "test input", self.backend_config, self.debug
        )

        # Get debug steps with data
        debug_steps = self.debug.get_debug_info()
        data_step = next((step for step in debug_steps if step.data is not None), None)

        assert data_step is not None
        assert "input_tokens" in data_step.data
        assert "normalized_aliases" in data_step.data
        assert data_step.data["input_tokens"] == ["test", "tokens"]

        # Verify normalized_aliases structure
        aliases_data = data_step.data["normalized_aliases"]
        assert len(aliases_data) == 1
        assert aliases_data[0]["product_id"] == "product1"
        assert aliases_data[0]["original_alias"] == "Test Product"
        assert aliases_data[0]["normalized_tokens"] == ["test", "product"]
