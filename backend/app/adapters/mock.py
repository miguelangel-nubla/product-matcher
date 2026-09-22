"""
Mock adapter for testing and development with comprehensive messy test data.
"""

from pathlib import Path
from typing import Any

import yaml

from app.adapters.base import (
    ExternalProduct,
    ProductDatabaseAdapter,
    extract_name_aliases,
)


class MockProductAdapter(ProductDatabaseAdapter):
    """
    Mock adapter for testing and development.
    Uses comprehensive messy test data that reflects real-world data quality issues.
    """

    @classmethod
    def from_config(cls, **config_kwargs: Any) -> "MockProductAdapter":
        """Mock adapter doesn't require any configuration."""
        return cls()

    def __init__(self) -> None:
        """Initialize with comprehensive messy test data."""
        self._products: dict[str, ExternalProduct] = {}
        self._load_test_data()

    def _load_test_data(self) -> None:
        """Load test data from YAML file."""
        bundled_path = Path(__file__).parent / "data" / "test_products_messy.yaml"
        test_data_path = (
            bundled_path
            if bundled_path.exists()
            else Path("tests/benchmarks/test_products_messy.yaml")
        )
        if not test_data_path.exists():
            repo_test_path = (
                Path(__file__).parents[2]
                / "tests"
                / "benchmarks"
                / "test_products_messy.yaml"
            )
            if repo_test_path.exists():
                test_data_path = repo_test_path

        if not test_data_path.exists():
            raise RuntimeError(
                f"Mock adapter requires test data file. Looked at: {bundled_path} and {test_data_path}. "
                "Please ensure the comprehensive test dataset exists."
            )

        with open(test_data_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            products_data = data.get("products", {})

            for product_id, product_info in products_data.items():
                name = product_info.get("name", "")
                aliases = product_info.get("aliases", [])

                # Create ExternalProduct with all aliases
                all_aliases = extract_name_aliases(name) if name else []
                all_aliases.extend([alias for alias in aliases if alias])

                # Skip completely empty products
                if not all_aliases:
                    continue

                self._products[product_id] = ExternalProduct(
                    id=product_id,
                    aliases=all_aliases,
                    description=f"Test product: {name}"
                    if name
                    else "Test product with data issues",
                    category="Test Category",
                    brand="Test Brand",
                    unit="unit",
                )

    def get_all_products(self) -> list[ExternalProduct]:
        """Mock implementation returning all products from external system."""
        return list(self._products.values())

    def get_product_details(self, product_id: str) -> ExternalProduct | None:
        """Mock implementation returning product details."""
        return self._products.get(product_id)

    def add_alias(self, product_id: str, alias: str) -> tuple[bool, str | None]:
        """Mock implementation - in real systems this would update the external system."""
        if product_id not in self._products:
            return False, f"Product '{product_id}' not found in mock database"

        # Check if alias already exists (case-insensitive)
        product = self._products[product_id]
        if alias.lower() in {a.lower() for a in product.aliases}:
            return True, None  # Already exists, consider it success

        # Mock: Add alias to the product and return success
        product.aliases.append(alias)
        if alias.isdigit() and len(alias) >= 8:
            if alias not in product.barcodes:
                product.barcodes.append(alias)
            if not product.barcode:
                product.barcode = alias
        return True, None

    def get_product_url(self, product_id: str) -> str | None:
        """
        Generate a mock external URL for demonstration.
        In a real system, this would link to the actual external product page.
        """
        if product_id not in self._products:
            return None

        # Mock URL for demonstration purposes
        return f"https://example-inventory.demo/products/{product_id}"


# Self-register the mock adapter
def _register_mock_adapter() -> None:
    try:
        from app.adapters.registry import registry

        registry.register("mock", MockProductAdapter)
    except ImportError:
        # Registry not available during import, skip registration
        pass


_register_mock_adapter()
