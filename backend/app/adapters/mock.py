"""
Mock adapter for testing and development.
"""

from typing import Any

from app.adapters.base import ExternalProduct, ProductDatabaseAdapter


class MockProductAdapter(ProductDatabaseAdapter):
    """
    Mock adapter for testing and development.
    Simulates an external product database with aliases.
    """

    @classmethod
    def from_config(cls, **config_kwargs: Any) -> "MockProductAdapter":
        """Mock adapter doesn't require any configuration."""
        return cls()

    def __init__(self) -> None:
        # Simulate external product database with aliases
        self._products = {
            "productId1": ExternalProduct(
                id="productId1",
                aliases=["Organic Apples", "organic red apples", "red apples"],
                description="Fresh organic red apples",
                category="Fruits",
                brand="FreshFarm",
                unit="kg",
            ),
            "productId2": ExternalProduct(
                id="productId2",
                aliases=["Whole Milk", "milk", "fresh milk"],
                description="Fresh whole milk",
                category="Dairy",
                brand="LocalDairy",
                unit="liter",
            ),
            "productId3": ExternalProduct(
                id="productId3",
                aliases=["Chocolate Cookies", "cookies", "choc cookies"],
                description="Dark chocolate chip cookies",
                category="Snacks",
                brand="SweetBite",
                unit="package",
            ),
            "productId4": ExternalProduct(
                id="productId4",
                aliases=["Red Apples", "red apple", "apples red"],
                description="Fresh red apples",
                category="Fruits",
                brand="FreshFarm",
                unit="kg",
            ),
            "productId5": ExternalProduct(
                id="productId5",
                aliases=["Las Manzanas Rojas", "manzanas rojas", "manzana roja"],
                description="Manzanas rojas frescas",
                category="Frutas",
                brand="FreshFarm",
                unit="kg",
            ),
        }

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

        # Check if alias already exists
        product = self._products[product_id]
        if alias in product.aliases:
            return True, None  # Already exists, consider it success

        # Mock: Add alias to the product and return success
        product.aliases.append(alias)
        return True, None

    def search_products(self, query: str, limit: int = 10) -> list[ExternalProduct]:
        """Mock implementation with simple text search."""
        query = query.lower()
        results = []

        for product in self._products.values():
            if (
                query in product.name.lower()
                or (product.description and query in product.description.lower())
                or (product.category and query in product.category.lower())
            ):
                results.append(product)

            if len(results) >= limit:
                break

        return results

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
