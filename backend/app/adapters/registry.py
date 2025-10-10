"""
Dynamic adapter registry with self-registration using YAML configuration.
"""

from app.adapters.base import ProductDatabaseAdapter
from app.config.loader import get_available_backends as get_yaml_backends
from app.config.loader import get_backend_config


class AdapterRegistry:
    """Registry for dynamically managing product database adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, type[ProductDatabaseAdapter]] = {}

    def register(self, name: str, adapter_class: type[ProductDatabaseAdapter]) -> None:
        """Register an adapter class."""
        self._adapters[name] = adapter_class

    def create_backend(self, backend_name: str) -> ProductDatabaseAdapter:
        """
        Create backend instance using YAML configuration.

        Args:
            backend_name: Backend instance name (e.g., "mock", "grocy1")

        Returns:
            Configured adapter instance

        Examples:
            For backend_name="mock":
            - Reads configuration from backends.yaml
            - Creates mock adapter instance

            For backend_name="grocy1":
            - Reads grocy1 configuration from backends.yaml
            - Creates grocy adapter with specified settings
        """
        # Get backend configuration from YAML
        backend_config = get_backend_config(backend_name)

        adapter_info = backend_config.adapter
        if not adapter_info:
            raise ValueError(f"Backend {backend_name} missing adapter configuration.")

        adapter_type = adapter_info.type
        if not adapter_type:
            raise ValueError(
                f"Backend {backend_name} missing adapter type in configuration."
            )

        if adapter_type not in self._adapters:
            raise ValueError(
                f"Unknown adapter type: {adapter_type}. Available: {list(self._adapters.keys())}"
            )

        # Extract adapter-specific config from the nested structure
        config = adapter_info.config

        adapter_class = self._adapters[adapter_type]
        return adapter_class.from_config(**config)

    def list_adapters(self) -> list[str]:
        """Get list of registered adapter names."""
        return list(self._adapters.keys())


# Global registry instance
registry = AdapterRegistry()


def _discover_adapters() -> None:
    """Dynamically discover and import all adapter modules."""
    import importlib
    import os

    # Get the adapters directory
    adapters_dir = os.path.dirname(__file__)

    # Import all Python files in the adapters directory
    for filename in os.listdir(adapters_dir):
        if (
            filename.endswith(".py")
            and not filename.startswith("__")
            and filename != "registry.py"
        ):
            module_name = filename[:-3]  # Remove .py extension
            try:
                importlib.import_module(f"app.adapters.{module_name}")
            except ImportError:
                pass  # Skip modules that can't be imported


def get_backend(backend_name: str) -> ProductDatabaseAdapter:
    """
    Get backend instance by name.

    Args:
        backend_name: Backend instance name (e.g., "backend1", "backend2")

    Returns:
        Configured adapter instance
    """
    # Discover and load all adapters dynamically
    _discover_adapters()

    return registry.create_backend(backend_name)


def get_backend_language(backend_name: str) -> str:
    """
    Get the configured language for a backend.

    Args:
        backend_name: Backend instance name (e.g., "mock", "grocy1")

    Returns:
        Language code (defaults to "en" if not configured)
    """
    try:
        backend_config = get_backend_config(backend_name)
        return backend_config.language
    except ValueError:
        # Backend not found, return default
        return "en"


def get_available_backends() -> list[str]:
    """
    Get list of available backend instance names from YAML configuration.

    Returns:
        List of backend names (e.g., ['mock', 'grocy1'])
    """
    try:
        return sorted(get_yaml_backends())
    except Exception:
        # If YAML loading fails, return just mock backend
        return ["mock"]
