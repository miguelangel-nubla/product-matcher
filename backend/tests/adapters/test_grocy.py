"""Test cases for the Grocy adapter."""

import pytest
from unittest.mock import Mock, patch
import httpx

from app.adapters.grocy import GrocyAdapter
from app.adapters.base import ExternalProduct


class TestGrocyAdapter:
    """Test cases for GrocyAdapter."""

    def test_from_config_success(self):
        """Test successful adapter creation from config."""
        config = {
            "base_url": "https://test.grocy.info",
            "api_key": "test-key",
            "external_url": "https://external.grocy.info"
        }

        adapter = GrocyAdapter.from_config(**config)

        assert adapter.base_url == "https://test.grocy.info"
        assert adapter.api_key == "test-key"
        assert adapter.external_url == "https://external.grocy.info"

    def test_from_config_missing_base_url(self):
        """Test adapter creation fails without base_url."""
        config = {"api_key": "test-key"}

        with pytest.raises(ValueError, match="Grocy adapter requires 'base_url' configuration"):
            GrocyAdapter.from_config(**config)

    def test_from_config_missing_api_key(self):
        """Test adapter creation fails without api_key."""
        config = {"base_url": "https://test.grocy.info"}

        with pytest.raises(ValueError, match="Grocy adapter requires 'api_key' configuration"):
            GrocyAdapter.from_config(**config)

    def test_init_with_trailing_slashes(self):
        """Test initialization removes trailing slashes."""
        adapter = GrocyAdapter(
            base_url="https://test.grocy.info/",
            api_key="test-key",
            external_url="https://external.grocy.info/"
        )

        assert adapter.base_url == "https://test.grocy.info"
        assert adapter.external_url == "https://external.grocy.info"

    def test_init_without_external_url(self):
        """Test initialization without external URL."""
        adapter = GrocyAdapter(
            base_url="https://test.grocy.info",
            api_key="test-key"
        )

        assert adapter.external_url is None

    @patch('httpx.Client')
    def test_get_reference_data_success(self, mock_client_class):
        """Test successful reference data retrieval."""
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock responses for each reference data endpoint
        mock_responses = [
            Mock(json=lambda: [{"id": 1, "name": "pieces"}, {"id": 2, "name": "kg"}]),  # quantity_units
            Mock(json=lambda: [{"id": 1, "name": "Fruits"}, {"id": 2, "name": "Dairy"}]),  # product_groups
            Mock(json=lambda: [{"id": 1, "name": "Fridge"}, {"id": 2, "name": "Pantry"}]),  # locations
        ]

        for response in mock_responses:
            response.raise_for_status.return_value = None

        mock_client.get.side_effect = mock_responses

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        reference_data = adapter._get_reference_data(mock_client)

        assert reference_data["quantity_units"]["1"] == "pieces"
        assert reference_data["quantity_units"]["2"] == "kg"
        assert reference_data["product_groups"]["1"] == "Fruits"
        assert reference_data["product_groups"]["2"] == "Dairy"
        assert reference_data["locations"]["1"] == "Fridge"
        assert reference_data["locations"]["2"] == "Pantry"

    @patch('httpx.Client')
    def test_get_reference_data_http_error(self, mock_client_class):
        """Test reference data retrieval with HTTP error."""
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        reference_data = adapter._get_reference_data(mock_client)

        # Should return empty dictionaries on error
        assert reference_data["quantity_units"] == {}
        assert reference_data["product_groups"] == {}
        assert reference_data["locations"] == {}

    def test_convert_grocy_product_basic(self):
        """Test basic product conversion."""
        grocy_product = {
            "id": 123,
            "name": "Milk",
            "description": "Fresh milk",
            "barcode": "1234567890"
        }
        reference_data = {
            "quantity_units": {},
            "product_groups": {},
            "locations": {}
        }

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        external_product = adapter._convert_grocy_product(grocy_product, reference_data)

        assert external_product.id == "123"
        assert external_product.aliases == ["Milk"]
        assert external_product.description == "Fresh milk"
        assert external_product.barcode == "1234567890"
        assert external_product.category is None
        assert external_product.unit is None

    def test_convert_grocy_product_with_userfields(self):
        """Test product conversion with userfield aliases."""
        grocy_product = {
            "id": 123,
            "name": "Milk",
            "userfields": {
                "ProductAltNames": "Whole Milk\nDairy Milk\n2% Milk"
            }
        }
        reference_data = {
            "quantity_units": {},
            "product_groups": {},
            "locations": {}
        }

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        external_product = adapter._convert_grocy_product(grocy_product, reference_data)

        assert external_product.aliases == ["Milk", "Whole Milk", "Dairy Milk", "2% Milk"]

    def test_convert_grocy_product_with_references(self):
        """Test product conversion with resolved references."""
        grocy_product = {
            "id": 123,
            "name": "Milk",
            "product_group_id": 2,
            "qu_id_stock": 1
        }
        reference_data = {
            "quantity_units": {"1": "liters"},
            "product_groups": {"2": "Dairy"},
            "locations": {}
        }

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        external_product = adapter._convert_grocy_product(grocy_product, reference_data)

        assert external_product.category == "Dairy"
        assert external_product.unit == "liters"

    @patch('httpx.Client')
    def test_get_all_products_success(self, mock_client_class):
        """Test successful retrieval of all products."""
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock reference data responses
        reference_responses = [
            Mock(json=lambda: [{"id": 1, "name": "pieces"}]),
            Mock(json=lambda: [{"id": 1, "name": "Fruits"}]),
            Mock(json=lambda: [{"id": 1, "name": "Fridge"}]),
        ]

        # Mock products response
        products_response = Mock(json=lambda: [
            {"id": 1, "name": "Apple", "description": "Red apple"},
            {"id": 2, "name": "Banana", "description": "Yellow banana"}
        ])

        for response in reference_responses + [products_response]:
            response.raise_for_status.return_value = None

        mock_client.get.side_effect = reference_responses + [products_response]

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        products = adapter.get_all_products()

        assert len(products) == 2
        assert products[0].id == "1"
        assert products[0].aliases == ["Apple"]
        assert products[1].id == "2"
        assert products[1].aliases == ["Banana"]

    @patch('httpx.Client')
    def test_get_all_products_http_error(self, mock_client_class):
        """Test get_all_products with HTTP error."""
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")

        with pytest.raises(RuntimeError, match="Unable to connect to Grocy"):
            adapter.get_all_products()

    @patch('httpx.Client')
    def test_get_product_details_success(self, mock_client_class):
        """Test successful product details retrieval."""
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock reference data and product responses
        reference_responses = [
            Mock(json=lambda: []),  # quantity_units
            Mock(json=lambda: []),  # product_groups
            Mock(json=lambda: []),  # locations
        ]

        product_response = Mock(json=lambda: {
            "id": 123,
            "name": "Milk",
            "description": "Fresh milk"
        })

        for response in reference_responses + [product_response]:
            response.raise_for_status.return_value = None

        mock_client.get.side_effect = reference_responses + [product_response]

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        product = adapter.get_product_details("123")

        assert product is not None
        assert product.id == "123"
        assert product.aliases == ["Milk"]

    @patch('httpx.Client')
    def test_get_product_details_not_found(self, mock_client_class):
        """Test product details retrieval when product not found."""
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_client.get.side_effect = httpx.HTTPError("404 Not Found")

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        product = adapter.get_product_details("999")

        assert product is None

    @patch('httpx.Client')
    def test_add_alias_success(self, mock_client_class):
        """Test successful alias addition."""
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock GET response for current product
        get_response = Mock(json=lambda: {
            "id": 123,
            "name": "Milk",
            "userfields": {"ProductAltNames": "Whole Milk"}
        })
        get_response.raise_for_status.return_value = None

        # Mock PUT response
        put_response = Mock()
        put_response.status_code = 200
        put_response.raise_for_status.return_value = None

        mock_client.get.return_value = get_response
        mock_client.put.return_value = put_response

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        success, error = adapter.add_alias("123", "2% Milk")

        assert success is True
        assert error is None

    @patch('httpx.Client')
    def test_add_alias_already_exists(self, mock_client_class):
        """Test adding alias that already exists."""
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        # Mock GET response with existing alias
        get_response = Mock(json=lambda: {
            "id": 123,
            "name": "Milk",
            "userfields": {"ProductAltNames": "Whole Milk\n2% Milk"}
        })
        get_response.raise_for_status.return_value = None

        mock_client.get.return_value = get_response

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        success, error = adapter.add_alias("123", "2% Milk")

        assert success is True
        assert error is None

    @patch('httpx.Client')
    def test_add_alias_http_error(self, mock_client_class):
        """Test alias addition with HTTP error."""
        mock_client = Mock()
        mock_client_class.return_value.__enter__.return_value = mock_client

        mock_client.get.side_effect = httpx.HTTPError("Connection failed")

        adapter = GrocyAdapter("https://test.grocy.info", "test-key")
        success, error = adapter.add_alias("123", "New Alias")

        assert success is False
        assert "HTTP error" in error

    def test_search_products(self):
        """Test product search functionality."""
        adapter = GrocyAdapter("https://test.grocy.info", "test-key")

        # Mock get_all_products
        mock_products = [
            ExternalProduct(id="1", aliases=["Apple"], description="Red apple"),
            ExternalProduct(id="2", aliases=["Banana"], description="Yellow banana"),
            ExternalProduct(id="3", aliases=["Orange"], description="Citrus fruit"),
        ]

        with patch.object(adapter, 'get_all_products', return_value=mock_products):
            results = adapter.search_products("apple", limit=10)

            assert len(results) == 1
            assert results[0].id == "1"

    def test_search_products_error(self):
        """Test product search with error."""
        adapter = GrocyAdapter("https://test.grocy.info", "test-key")

        with patch.object(adapter, 'get_all_products', side_effect=Exception("Test error")):
            results = adapter.search_products("apple")

            assert results == []

    def test_get_product_url_with_external_url(self):
        """Test product URL generation with external URL configured."""
        adapter = GrocyAdapter(
            "https://test.grocy.info",
            "test-key",
            external_url="https://external.grocy.info"
        )

        url = adapter.get_product_url("123")
        assert url == "https://external.grocy.info/product/123"

    def test_get_product_url_without_external_url(self):
        """Test product URL generation without external URL."""
        adapter = GrocyAdapter("https://test.grocy.info", "test-key")

        url = adapter.get_product_url("123")
        assert url is None
