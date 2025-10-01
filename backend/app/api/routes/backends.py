"""
Backend API routes for accessing backend-specific resources.
"""

from typing import Any

from fastapi import APIRouter

from app.adapters.registry import get_backend

router = APIRouter()


@router.get("/{backend}/product/{product_id}/url")
def get_product_url(backend: str, product_id: str) -> Any:
    """
    Get external URL for a product in the specified backend.
    """
    # Get specified backend from registry
    adapter = get_backend(backend)

    # Get product URL from adapter
    product_url = adapter.get_product_url(product_id)

    return {"product_id": product_id, "backend": backend, "url": product_url}
