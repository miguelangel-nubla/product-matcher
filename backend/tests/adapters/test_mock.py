"""
Simple tests for mock adapter.
"""
import pytest

from app.adapters.mock import MockProductAdapter


class TestMockAdapter:
    """Test MockProductAdapter functionality."""

    @pytest.fixture
    def adapter(self):
        """MockProductAdapter instance for testing."""
        return MockProductAdapter()

    def test_get_all_products(self, adapter):
        """Test getting all products from mock adapter."""
        products = adapter.get_all_products()
        assert isinstance(products, list)
        assert len(products) > 0

    def test_get_product_details(self, adapter):
        """Test getting product details."""
        product = adapter.get_product_details("productId1")
        assert product is not None
        assert product.id == "productId1"

    def test_add_alias_success(self, adapter):
        """Test adding alias to mock adapter."""
        success, error = adapter.add_alias("productId1", "New Alias")
        assert success is True
        assert error is None

    def test_add_alias_not_found(self, adapter):
        """Test adding alias to non-existent product."""
        success, error = adapter.add_alias("nonexistent", "New Alias")
        assert success is False
        assert error is not None

    def test_search_products(self, adapter):
        """Test searching products."""
        results = adapter.search_products("apple")
        assert isinstance(results, list)

    def test_get_product_url(self, adapter):
        """Test getting product URL."""
        url = adapter.get_product_url("productId1")
        assert url is not None
        assert "productId1" in url
