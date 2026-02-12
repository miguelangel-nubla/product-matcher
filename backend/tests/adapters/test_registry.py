"""Test cases for the adapter registry."""

import pytest
import app.adapters.registry as registry_module
from unittest.mock import Mock, patch, mock_open
import os

from app.adapters.registry import AdapterRegistry, registry, get_backend, get_backend_language, get_available_backends, _discover_adapters
from app.adapters.base import ProductDatabaseAdapter
from app.models import BackendConfig, AdapterConfig


class MockAdapter(ProductDatabaseAdapter):
    """Mock adapter for testing."""

    @classmethod
    def from_config(cls, **config_kwargs):
        return cls(**config_kwargs)

    def __init__(self, **kwargs):
        self.config = kwargs

    def get_all_products(self):
        return []

    def get_product_details(self, product_id):
        return None

    def search_products(self, query, limit=10):
        return []

    def add_alias(self, product_id, alias):
        return True


class TestAdapterRegistry:
    """Test cases for AdapterRegistry."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = AdapterRegistry()

    def test_init(self):
        """Test registry initialization."""
        assert self.registry._adapters == {}

    def test_register(self):
        """Test adapter registration."""
        self.registry.register("test", MockAdapter)

        assert "test" in self.registry._adapters
        assert self.registry._adapters["test"] == MockAdapter

    def test_list_adapters_empty(self):
        """Test listing adapters when empty."""
        assert self.registry.list_adapters() == []

    def test_list_adapters_with_registered(self):
        """Test listing adapters with registered adapters."""
        self.registry.register("mock", MockAdapter)
        self.registry.register("test", MockAdapter)

        adapters = self.registry.list_adapters()
        assert set(adapters) == {"mock", "test"}

    @patch('app.adapters.registry.get_backend_config')
    def test_create_backend_success(self, mock_get_config):
        """Test successful backend creation."""
        # Mock backend configuration
        mock_config = BackendConfig(
            description="Test backend",
            language="en",
            adapter=AdapterConfig(type="mock", config={"test_param": "value"})
        )
        mock_get_config.return_value = mock_config

        # Register adapter
        self.registry.register("mock", MockAdapter)

        # Create backend
        backend = self.registry.create_backend("test-backend")

        assert isinstance(backend, MockAdapter)
        assert backend.config["test_param"] == "value"
        mock_get_config.assert_called_once_with("test-backend")

    @patch('app.adapters.registry.get_backend_config')
    def test_create_backend_config_not_found(self, mock_get_config):
        """Test backend creation when configuration not found."""
        mock_get_config.side_effect = ValueError("Backend not found")

        with pytest.raises(ValueError, match="Backend not found"):
            self.registry.create_backend("test-backend")

    @patch('app.adapters.registry.get_backend_config')
    def test_create_backend_missing_adapter_config(self, mock_get_config):
        """Test backend creation with missing adapter configuration."""
        # Create a mock that bypasses pydantic validation
        mock_config = Mock()
        mock_config.adapter = None
        mock_get_config.return_value = mock_config

        with pytest.raises(ValueError, match="missing adapter configuration"):
            self.registry.create_backend("test-backend")

    @patch('app.adapters.registry.get_backend_config')
    def test_create_backend_missing_adapter_type(self, mock_get_config):
        """Test backend creation with missing adapter type."""
        mock_config = BackendConfig(
            description="Test backend",
            language="en",
            adapter=AdapterConfig(type="", config={})
        )
        mock_get_config.return_value = mock_config

        with pytest.raises(ValueError, match="missing adapter type"):
            self.registry.create_backend("test-backend")

    @patch('app.adapters.registry.get_backend_config')
    def test_create_backend_unknown_adapter_type(self, mock_get_config):
        """Test backend creation with unknown adapter type."""
        mock_config = BackendConfig(
            description="Test backend",
            language="en",
            adapter=AdapterConfig(type="unknown", config={})
        )
        mock_get_config.return_value = mock_config

        with pytest.raises(ValueError, match="Unknown adapter type: unknown"):
            self.registry.create_backend("test-backend")

    @patch('app.adapters.registry.get_backend_config')
    def test_create_backend_adapter_from_config_error(self, mock_get_config):
        """Test backend creation when adapter from_config fails."""
        mock_config = BackendConfig(
            description="Test backend",
            language="en",
            adapter=AdapterConfig(type="mock", config={"invalid": "config"})
        )
        mock_get_config.return_value = mock_config

        # Create mock adapter that raises error
        mock_adapter_class = Mock()
        mock_adapter_class.from_config.side_effect = Exception("Config error")
        self.registry.register("mock", mock_adapter_class)

        with pytest.raises(Exception, match="Config error"):
            self.registry.create_backend("test-backend")


class TestRegistryFunctions:
    """Test cases for registry module functions."""

    @patch('app.adapters.registry._discover_adapters')
    @patch('app.adapters.registry.registry')
    def test_get_backend(self, mock_registry, mock_discover):
        """Test get_backend function."""
        mock_backend = Mock()
        mock_registry.create_backend.return_value = mock_backend

        result = get_backend("test-backend")

        assert result == mock_backend
        mock_discover.assert_called_once()
        mock_registry.create_backend.assert_called_once_with("test-backend")

    @patch('app.adapters.registry.get_backend_config')
    def test_get_backend_language_success(self, mock_get_config):
        """Test successful backend language retrieval."""
        mock_config = BackendConfig(
            description="Test backend",
            language="es",
            adapter=AdapterConfig(type="mock", config={})
        )
        mock_get_config.return_value = mock_config

        result = get_backend_language("test-backend")

        assert result == "es"
        mock_get_config.assert_called_once_with("test-backend")

    @patch('app.adapters.registry.get_backend_config')
    def test_get_backend_language_not_found(self, mock_get_config):
        """Test backend language retrieval when backend not found."""
        mock_get_config.side_effect = ValueError("Backend not found")

        result = get_backend_language("invalid-backend")

        assert result == "en"  # Default language

    @patch('app.adapters.registry.get_yaml_backends')
    def test_get_available_backends_success(self, mock_get_yaml):
        """Test successful available backends retrieval."""
        mock_get_yaml.return_value = ["grocy1", "mock", "grocy2"]

        result = get_available_backends()

        assert result == ["grocy1", "grocy2", "mock"]  # Sorted
        mock_get_yaml.assert_called_once()

    @patch('app.adapters.registry.get_yaml_backends')
    def test_get_available_backends_error(self, mock_get_yaml):
        """Test available backends retrieval with error."""
        mock_get_yaml.side_effect = Exception("YAML error")

        result = get_available_backends()

        assert result == ["mock"]  # Fallback

    @patch('os.listdir')
    @patch('os.path.dirname')
    @patch('importlib.import_module')
    def test_discover_adapters_success(self, mock_import, mock_dirname, mock_listdir):
        """Test successful adapter discovery."""
        mock_dirname.return_value = "/path/to/adapters"
        mock_listdir.return_value = [
            "__init__.py",
            "registry.py",
            "mock.py",
            "grocy.py",
            "__pycache__",
            "base.py"
        ]

        _discover_adapters()

        # Should import mock, grocy, and base modules
        expected_calls = [
            "app.adapters.mock",
            "app.adapters.grocy",
            "app.adapters.base"
        ]

        actual_calls = [call[0][0] for call in mock_import.call_args_list]
        # Check that expected calls sort of happened (subset)
        for expected in expected_calls:
             assert expected in actual_calls


    @patch('importlib.import_module')
    def test_discover_adapters_import_error(self, mock_import):
        """Test adapter discovery with import errors."""
        # Create dummy broken.py
        adapters_dir = os.path.dirname(registry_module.__file__)
        broken_py = os.path.join(adapters_dir, "broken.py")

        with open(broken_py, "w") as f:
            f.write("")

        try:
            # Mock import to fail for broken.py but succeed for others
            def side_effect(module_name):
                if "broken" in module_name:
                    raise ImportError("Broken module")
                return Mock()

            mock_import.side_effect = side_effect

            # Should not raise exception
            _discover_adapters()

            # Should have attempted to import broken
            actual_calls = [call[0][0] for call in mock_import.call_args_list]
            assert "app.adapters.broken" in actual_calls

        finally:
            # Clean up
            if os.path.exists(broken_py):
                os.remove(broken_py)

    @patch('os.listdir')
    @patch('os.path.dirname')
    def test_discover_adapters_no_python_files(self, mock_dirname, mock_listdir):
        """Test adapter discovery with no Python files."""
        mock_dirname.return_value = "/path/to/adapters"
        mock_listdir.return_value = ["README.md", "config.yaml"]

        # Should not raise exception
        _discover_adapters()

    @patch('os.listdir')
    @patch('os.path.dirname')
    def test_discover_adapters_os_error(self, mock_dirname, mock_listdir):
        """Test adapter discovery with OS error."""
        mock_dirname.return_value = "/path/to/adapters"
        mock_listdir.side_effect = OSError("Directory not found")

        # Should raise exception since there's no error handling for OSError
        with pytest.raises(OSError, match="Directory not found"):
            _discover_adapters()


class TestGlobalRegistry:
    """Test cases for global registry instance."""

    def test_global_registry_exists(self):
        """Test that global registry instance exists."""
        assert registry is not None
        assert isinstance(registry, AdapterRegistry)

    def test_global_registry_can_register(self):
        """Test that global registry can register adapters."""
        initial_count = len(registry.list_adapters())

        registry.register("test_global", MockAdapter)

        assert len(registry.list_adapters()) == initial_count + 1
        assert "test_global" in registry.list_adapters()

        # Clean up
        registry._adapters.pop("test_global", None)
