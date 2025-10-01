"""
Grocy adapter for ProductMatcher.
Implements live integration with Grocy inventory management system.
"""

import logging
from typing import Any

import httpx

from app.adapters.base import ExternalProduct, ProductDatabaseAdapter

logger = logging.getLogger(__name__)


class GrocyAdapter(ProductDatabaseAdapter):
    """
    Grocy adapter that integrates with Grocy API for live product data.

    Grocy API documentation: https://demo.grocy.info/api
    """

    @classmethod
    def from_config(cls, **config_kwargs: Any) -> "GrocyAdapter":
        """
        Create Grocy adapter from configuration.

        Required config:
            - base_url: Grocy instance URL
            - api_key: Grocy API key

        Args:
            **config_kwargs: Configuration parameters

        Returns:
            Configured GrocyAdapter instance

        Raises:
            ValueError: If required configuration is missing
        """
        base_url = config_kwargs.get("base_url")
        api_key = config_kwargs.get("api_key")

        if not base_url:
            raise ValueError("Grocy adapter requires 'base_url' configuration")
        if not api_key:
            raise ValueError("Grocy adapter requires 'api_key' configuration")

        external_url = config_kwargs.get("external_url")
        return cls(base_url=base_url, api_key=api_key, external_url=external_url)

    def __init__(self, base_url: str, api_key: str, external_url: str | None = None):
        """
        Initialize Grocy adapter.

        Args:
            base_url: Grocy instance URL (e.g., "https://demo.grocy.info")
            api_key: Grocy API key for authentication
            external_url: External URL base for generating product links (optional)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.external_url = external_url.rstrip("/") if external_url else None
        self.headers = {"GROCY-API-KEY": api_key, "Content-Type": "application/json"}

    def _get_reference_data(self, client: httpx.Client) -> dict[str, dict[str, str]]:
        """
        Get reference data from Grocy (quantity units, product groups, locations).

        Returns:
            Dictionary with reference data for resolving IDs to names
        """
        reference_data: dict[str, dict[str, str]] = {
            "quantity_units": {},
            "product_groups": {},
            "locations": {},
        }

        try:
            # Get quantity units
            response = client.get(
                f"{self.base_url}/api/objects/quantity_units", headers=self.headers
            )
            response.raise_for_status()
            for unit in response.json():
                reference_data["quantity_units"][str(unit["id"])] = unit["name"]

            # Get product groups
            response = client.get(
                f"{self.base_url}/api/objects/product_groups", headers=self.headers
            )
            response.raise_for_status()
            for group in response.json():
                reference_data["product_groups"][str(group["id"])] = group["name"]

            # Get locations
            response = client.get(
                f"{self.base_url}/api/objects/locations", headers=self.headers
            )
            response.raise_for_status()
            for location in response.json():
                reference_data["locations"][str(location["id"])] = location["name"]

        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch some reference data from Grocy: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error fetching reference data: {e}")

        return reference_data

    def get_all_products(self) -> list[ExternalProduct]:
        """
        Get all products from Grocy including aliases from userfield.
        Fetches reference data once per call for efficient lookup.

        Returns:
            List of all products available in Grocy
        """
        try:
            with httpx.Client() as client:
                # Get reference data once per call (3 API calls total)
                reference_data = self._get_reference_data(client)

                # Get all products from Grocy (1 API call)
                response = client.get(
                    f"{self.base_url}/api/objects/products", headers=self.headers
                )
                response.raise_for_status()

                grocy_products = response.json()
                external_products = []

                # Process all products with the cached reference data
                for grocy_product in grocy_products:
                    external_products.append(
                        self._convert_grocy_product(grocy_product, reference_data)
                    )

                logger.info(
                    f"Retrieved {len(external_products)} products from Grocy with reference data"
                )
                return external_products

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch products from Grocy: {e}")
            raise RuntimeError(f"Unable to connect to Grocy at {self.base_url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching products from Grocy: {e}")
            raise RuntimeError(f"Grocy adapter error: {e}")

    def _convert_grocy_product(
        self, grocy_product: dict[str, Any], reference_data: dict[str, dict[str, str]]
    ) -> ExternalProduct:
        """
        Convert a Grocy product dict to ExternalProduct using reference data.

        Args:
            grocy_product: Raw product data from Grocy API
            reference_data: Lookup tables for IDs to names

        Returns:
            ExternalProduct with resolved names
        """
        # Start with the product name as first alias
        aliases = [grocy_product["name"]]

        # Add aliases from ProductAltNames userfield if present
        userfields = grocy_product.get("userfields", {})
        userfield_value = userfields.get("ProductAltNames", "")
        if userfield_value:
            userfield_aliases = [
                alias.strip() for alias in userfield_value.split("\n") if alias.strip()
            ]
            aliases.extend(userfield_aliases)

        # Resolve category from product_group_id
        category = None
        product_group_id = grocy_product.get("product_group_id")
        if product_group_id:
            category = reference_data["product_groups"].get(str(product_group_id))

        # Resolve unit from qu_id_stock
        unit = None
        qu_id_stock = grocy_product.get("qu_id_stock")
        if qu_id_stock:
            unit = reference_data["quantity_units"].get(str(qu_id_stock))

        return ExternalProduct(
            id=str(grocy_product["id"]),
            aliases=aliases,
            description=grocy_product.get("description"),
            category=category,
            brand=None,  # Grocy doesn't have a standard brand field
            unit=unit,
            barcode=grocy_product.get("barcode"),
        )

    def get_product_details(self, product_id: str) -> ExternalProduct | None:
        """
        Get detailed information about a specific Grocy product.

        Args:
            product_id: Grocy product ID

        Returns:
            ExternalProduct with full details or None if not found
        """
        try:
            with httpx.Client() as client:
                # Get reference data for this single product lookup
                reference_data = self._get_reference_data(client)

                response = client.get(
                    f"{self.base_url}/api/objects/products/{product_id}",
                    headers=self.headers,
                )
                response.raise_for_status()

                grocy_product = response.json()
                return self._convert_grocy_product(grocy_product, reference_data)

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch product {product_id} from Grocy: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error fetching product {product_id} from Grocy: {e}"
            )
            return None

    def add_alias(self, product_id: str, alias: str) -> tuple[bool, str | None]:
        """
        Add a learned alias to Grocy ProductAltNames userfield.

        Appends the alias to the existing userfield with newline separation.

        Args:
            product_id: Grocy product ID
            alias: New alias to add

        Returns:
            Tuple of (success, error_message)
        """
        try:
            with httpx.Client() as client:
                # First, get current userfield value
                response = client.get(
                    f"{self.base_url}/api/objects/products/{product_id}",
                    headers=self.headers,
                )
                response.raise_for_status()

                grocy_product = response.json()
                userfields = grocy_product.get("userfields", {})
                current_aliases = userfields.get("ProductAltNames", "")

                # Check if alias already exists
                existing_aliases = [
                    a.strip() for a in (current_aliases or "").split("\n") if a.strip()
                ]
                if alias in existing_aliases:
                    logger.info(
                        f"Alias '{alias}' already exists for product {product_id}"
                    )
                    return True, None

                # Add new alias
                if current_aliases:
                    new_aliases_text = current_aliases + "\n" + alias
                else:
                    new_aliases_text = alias

                # Use the dedicated userfields endpoint as per Grocy OpenAPI spec
                userfield_data = {"ProductAltNames": new_aliases_text}

                logger.info(
                    f"Sending PUT request to update userfields for product {product_id} with data: {userfield_data}"
                )

                response = client.put(
                    f"{self.base_url}/api/userfields/products/{product_id}",
                    headers=self.headers,
                    json=userfield_data,
                )

                logger.info(f"PUT response status: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"PUT response body: {response.text}")
                response.raise_for_status()

                logger.info(f"Added alias '{alias}' to product {product_id} in Grocy")
                return True, None

        except httpx.HTTPError as e:
            error_msg = f"HTTP error adding alias to product {product_id} in Grocy: {e}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error adding alias to product {product_id}: {e}"
            logger.error(error_msg)
            return False, error_msg

    def search_products(self, query: str, limit: int = 10) -> list[ExternalProduct]:
        """
        Search products in Grocy.

        Uses Grocy's search functionality if available, otherwise falls back
        to client-side filtering.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching products
        """
        try:
            # Get all products and filter client-side
            # Note: Grocy API may have search endpoints - check documentation
            all_products = self.get_all_products()

            query_lower = query.lower()
            matching_products = []

            for product in all_products:
                if query_lower in product.name.lower() or (
                    product.description and query_lower in product.description.lower()
                ):
                    matching_products.append(product)

                    if len(matching_products) >= limit:
                        break

            return matching_products

        except Exception as e:
            logger.error(f"Error searching products in Grocy: {e}")
            return []

    def get_product_url(self, product_id: str) -> str | None:
        """
        Generate external URL for a Grocy product.

        Args:
            product_id: Grocy product ID

        Returns:
            URL to view the product in Grocy, or None if external_url not configured
        """
        if not self.external_url:
            return None

        return f"{self.external_url}/product/{product_id}"


# Self-register the Grocy adapter
def _register_grocy_adapter() -> None:
    try:
        from app.adapters.registry import registry

        registry.register("grocy", GrocyAdapter)
    except ImportError:
        # Registry not available during import, skip registration
        pass


_register_grocy_adapter()
