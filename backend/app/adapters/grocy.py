"""
Grocy adapter for ProductMatcher.
Implements live integration with Grocy inventory management system.
"""

import logging
import time
from typing import Any

import httpx

from app.adapters.base import (
    ExternalProduct,
    ProductDatabaseAdapter,
    extract_name_aliases,
)

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

        Optional config:
            - external_url: External URL base for product links
            - ignore_prefixes: List of string prefixes (or single string) to exclude products

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
        ignore_prefixes = config_kwargs.get("ignore_prefixes") or config_kwargs.get(
            "ignore_product_prefixes"
        )
        return cls(
            base_url=base_url,
            api_key=api_key,
            external_url=external_url,
            ignore_prefixes=ignore_prefixes,
        )

    def __init__(
        self,
        base_url: str,
        api_key: str,
        external_url: str | None = None,
        ignore_prefixes: list[str] | str | None = None,
    ):
        """
        Initialize Grocy adapter.

        Args:
            base_url: Grocy instance URL (e.g., "https://demo.grocy.info")
            api_key: Grocy API key for authentication
            external_url: External URL base for generating product links (optional)
            ignore_prefixes: Product name prefixes to exclude (e.g., ["*"])
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.external_url = external_url.rstrip("/") if external_url else None
        if isinstance(ignore_prefixes, str):
            self.ignore_prefixes: tuple[str, ...] = (ignore_prefixes,)
        elif ignore_prefixes:
            self.ignore_prefixes = tuple(str(p) for p in ignore_prefixes if p)
        else:
            self.ignore_prefixes = ()

        self.headers = {"GROCY-API-KEY": api_key, "Content-Type": "application/json"}
        self._cached_products: list[ExternalProduct] | None = None
        self._cached_products_time: float = 0
        self._cached_reference_data: dict[str, Any] | None = None
        self._cached_reference_time: float = 0
        self._cache_ttl_seconds: float = 300.0

    def invalidate_cache(self) -> None:
        """Invalidate cached products and reference data."""
        self._cached_products = None
        self._cached_products_time = 0
        self._cached_reference_data = None
        self._cached_reference_time = 0

    def _get_reference_data(self, client: httpx.Client) -> dict[str, Any]:
        """
        Get reference data from Grocy (quantity units, product groups, locations, barcodes).

        Returns:
            Dictionary with reference data for resolving IDs to names and barcodes
        """
        if (
            self._cached_reference_data is not None
            and time.time() - self._cached_reference_time < self._cache_ttl_seconds
        ):
            return self._cached_reference_data

        reference_data: dict[str, Any] = {
            "quantity_units": {},
            "product_groups": {},
            "locations": {},
            "barcodes": {},
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

            # Get product barcodes
            try:
                response = client.get(
                    f"{self.base_url}/api/objects/product_barcodes",
                    headers=self.headers,
                )
                response.raise_for_status()
                for item in response.json():
                    pid = str(item.get("product_id"))
                    code = item.get("barcode")
                    if code:
                        reference_data["barcodes"].setdefault(pid, []).append(str(code))
            except Exception as e:
                logger.warning(f"Failed to fetch product barcodes from Grocy: {e}")

        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch some reference data from Grocy: {e}")
            return reference_data
        except Exception as e:
            logger.warning(f"Unexpected error fetching reference data: {e}")
            return reference_data

        self._cached_reference_data = reference_data
        self._cached_reference_time = time.time()
        return reference_data

    def get_all_products(self) -> list[ExternalProduct]:
        """
        Get all products from Grocy including aliases from userfield.
        Fetches reference data once per call for efficient lookup.
        Filters out products starting with any prefix in ignore_prefixes.

        Returns:
            List of all active, non-ignored products available in Grocy
        """
        if (
            self._cached_products is not None
            and time.time() - self._cached_products_time < self._cache_ttl_seconds
        ):
            return self._cached_products

        try:
            with httpx.Client() as client:
                # Get reference data once per call (quantity units, groups, locations, barcodes)
                reference_data = self._get_reference_data(client)

                # Get all products from Grocy (1 API call)
                response = client.get(
                    f"{self.base_url}/api/objects/products",
                    headers=self.headers,
                    params={"query[]": "no_own_stock=0"},
                )
                response.raise_for_status()

                grocy_products = response.json()
                external_products = []

                # Process all products with the cached reference data
                for grocy_product in grocy_products:
                    if str(grocy_product.get("active", "1")) in ("0", "false"):
                        continue
                    name = grocy_product.get("name", "").strip()
                    if self.ignore_prefixes and name.startswith(self.ignore_prefixes):
                        continue
                    external_products.append(
                        self._convert_grocy_product(grocy_product, reference_data)
                    )

                logger.info(
                    f"Retrieved {len(external_products)} products from Grocy with reference data"
                )
                self._cached_products = external_products
                self._cached_products_time = time.time()
                return external_products

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch products from Grocy: {e}")
            raise RuntimeError(f"Unable to connect to Grocy at {self.base_url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching products from Grocy: {e}")
            raise RuntimeError(f"Grocy adapter error: {e}")

    def _convert_grocy_product(
        self, grocy_product: dict[str, Any], reference_data: dict[str, Any]
    ) -> ExternalProduct:
        """
        Convert a Grocy product dict to ExternalProduct using reference data.

        Args:
            grocy_product: Raw product data from Grocy API
            reference_data: Lookup tables for IDs to names and barcodes

        Returns:
            ExternalProduct with resolved names and barcodes
        """
        # Start with candidate aliases extracted from the product name
        # (expands slashes like 'Barquillos/rollitos' and parentheses like 'Maizena (fécula de maiz)')
        aliases = extract_name_aliases(grocy_product.get("name", ""))

        # Add aliases from ProductAltNames userfield if present
        userfields = grocy_product.get("userfields") or {}
        userfield_value = userfields.get("ProductAltNames") or ""
        if userfield_value:
            userfield_aliases = [
                alias.strip() for alias in userfield_value.split("\n") if alias.strip()
            ]
            aliases.extend(userfield_aliases)

        # Deduplicate while preserving order (case-insensitive)
        seen: set[str] = set()
        deduped_aliases: list[str] = []
        for a in aliases:
            cleaned = a.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                deduped_aliases.append(cleaned)

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

        product_id_str = str(grocy_product["id"])
        product_barcodes = reference_data.get("barcodes", {}).get(product_id_str, [])
        primary_barcode = (
            product_barcodes[0] if product_barcodes else grocy_product.get("barcode")
        )

        return ExternalProduct(
            id=product_id_str,
            aliases=deduped_aliases,
            description=grocy_product.get("description"),
            category=category,
            brand=None,  # Grocy doesn't have a standard brand field
            unit=unit,
            barcode=primary_barcode,
            barcodes=product_barcodes,
        )

    def get_product_details(self, product_id: str) -> ExternalProduct | None:
        """
        Get detailed information about a specific Grocy product.

        Args:
            product_id: Grocy product ID

        Returns:
            ExternalProduct with full details or None if not found or ignored
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
                if str(grocy_product.get("active", "1")) in ("0", "false"):
                    return None
                name = grocy_product.get("name", "").strip()
                if self.ignore_prefixes and name.startswith(self.ignore_prefixes):
                    return None
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
        If the alias is a barcode, also registers it in Grocy's product_barcodes table.

        Appends the alias to the existing userfield with newline separation.

        Args:
            product_id: Grocy product ID
            alias: New alias to add

        Returns:
            Tuple of (success, error_message)
        """
        if not alias or not alias.strip():
            return False, "Alias cannot be empty"
        alias = alias.strip()

        try:
            with httpx.Client() as client:
                # First, get current product and userfield value
                response = client.get(
                    f"{self.base_url}/api/objects/products/{product_id}",
                    headers=self.headers,
                )
                response.raise_for_status()

                grocy_product = response.json()
                if str(grocy_product.get("active", "1")) in ("0", "false"):
                    return False, f"Product {product_id} is inactive"

                product_name = grocy_product.get("name", "").strip()
                if self.ignore_prefixes and product_name.startswith(
                    self.ignore_prefixes
                ):
                    return (
                        False,
                        f"Product '{product_name}' matches ignored prefixes and cannot be modified",
                    )

                # If alias is a barcode, register in Grocy's product_barcodes table
                if alias.isdigit() and len(alias) >= 8:
                    try:
                        client.post(
                            f"{self.base_url}/api/objects/product_barcodes",
                            headers=self.headers,
                            json={"product_id": int(product_id), "barcode": alias},
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to add barcode to Grocy product_barcodes for product {product_id}: {e}"
                        )

                userfields = grocy_product.get("userfields") or {}
                current_aliases = userfields.get("ProductAltNames") or ""

                # Check if alias already exists (case-insensitive check against existing aliases and product name)
                existing_aliases = [
                    a.strip() for a in current_aliases.split("\n") if a.strip()
                ]
                existing_lower = {a.lower() for a in existing_aliases}
                if product_name:
                    existing_lower.add(product_name.lower())

                if alias.lower() in existing_lower:
                    logger.info(
                        f"Alias '{alias}' already exists for product {product_id}"
                    )
                    return True, None

                # Add new alias cleanly without preserving any blank lines
                new_aliases = existing_aliases + [alias]
                new_aliases_text = "\n".join(new_aliases)

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
                if response.status_code not in (200, 204):
                    logger.error(f"PUT response body: {response.text}")
                response.raise_for_status()

                self.invalidate_cache()
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
