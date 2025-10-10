"""
Database adapter interface for external inventory systems.
Implements the database-agnostic pattern from the architecture.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ExternalProduct:
    """
    Represents a product from an external inventory system.
    This is the standardized format that all adapters must return.
    """

    id: str  # External product ID (can be any format)
    aliases: list[str]  # First alias is the primary name, rest are alternatives
    description: str | None = None
    category: str | None = None
    brand: str | None = None
    unit: str | None = None
    barcode: str | None = None

    @property
    def name(self) -> str:
        """Primary name is the first alias."""
        return self.aliases[0] if self.aliases else ""


class ProductDatabaseAdapter(ABC):
    """
    Abstract adapter interface for external product databases.

    This implements the live database-agnostic interface:
    - get_all_products() → returns all products from external system
    - get_product_details(product_id) → get specific product details
    - search_products(query) → search for products (used for manual resolution)

    The adapter handles live communication with external systems (Grocy, ERP, etc.)
    ProductMatcher only stores pending items - all product data is read live.

    Each adapter implementation should handle its own configuration independently.
    """

    @classmethod
    @abstractmethod
    def from_config(cls, **config_kwargs: Any) -> "ProductDatabaseAdapter":
        """
        Create adapter instance from configuration.
        Each adapter defines its own required config parameters.

        Args:
            **config_kwargs: Adapter-specific configuration

        Returns:
            Configured adapter instance

        Raises:
            ValueError: If required configuration is missing
        """
        pass

    @abstractmethod
    def get_all_products(self) -> list[ExternalProduct]:
        """
        Get all products from the external system for live matching.

        Returns:
            List of all products available in the external system
        """
        pass

    @abstractmethod
    def get_product_details(self, product_id: str) -> ExternalProduct | None:
        """
        Get detailed information about a specific product.

        Args:
            product_id: External product ID

        Returns:
            ExternalProduct with full details or None if not found
        """
        pass

    @abstractmethod
    def add_alias(self, product_id: str, alias: str) -> tuple[bool, str | None]:
        """
        Add a learned alias to the external system.

        For Grocy: adds the alias to the userfield (newline-separated).
        Other systems may handle this differently.

        Args:
            product_id: External product ID
            alias: New alias to associate with the product

        Returns:
            Tuple of (success, error_message). error_message is None on success.
        """
        pass

    @abstractmethod
    def search_products(self, query: str, limit: int = 10) -> list[ExternalProduct]:
        """
        Search products in the external system.
        Used for manual resolution and product discovery.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching products
        """
        pass

    def get_product_url(self, product_id: str) -> str | None:
        """
        Generate external URL for a product.
        Override this method in adapters that support external URLs.

        Args:
            product_id: External product ID

        Returns:
            URL to view the product in the external system, or None if not supported
        """
        return None

    def get_all_aliases(self) -> list[tuple[str, str]]:
        """
        Get all aliases from all products as (product_id, alias) tuples.
        Default implementation extracts aliases from get_all_products().

        Returns:
            List of (product_id, alias) tuples
        """
        products = self.get_all_products()
        aliases = []
        for product in products:
            if hasattr(product, "aliases") and product.aliases:
                for alias in product.aliases:
                    aliases.append((product.id, alias))
        return aliases
