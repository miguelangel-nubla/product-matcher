"""
Product matching API routes.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.adapters.registry import get_backend
from app.api.deps import CurrentUser, SessionDep
from app.config.loader import get_global_settings
from app.models import (
    BackendInfo,
    GlobalSettings,
    MatchLog,
    MatchRequest,
    MatchResult,
    Message,
    PendingQueriesPublic,
    PendingQuery,
    PendingQueryPublic,
    ResolveRequest,
)
from app.services.matcher import ProductMatcher
from app.services.pending import PendingQueueManager

router = APIRouter()


@router.post("/match", response_model=MatchResult)
def match_product(
    *, session: SessionDep, current_user: CurrentUser, query: MatchRequest
) -> Any:
    """
    Match a text string against external product database.
    Returns either a matched product or adds to pending queue.
    """
    # Get specified backend from registry
    adapter = get_backend(query.backend)
    matcher = ProductMatcher(session, adapter)

    # Get the language configured for this backend
    from app.adapters.registry import get_backend_language

    language = get_backend_language(query.backend)

    # Attempt to match the product
    try:
        success, normalized_input, candidates, debug_info = matcher.match_product(
            text=query.text,
            backend_name=query.backend,
            threshold=query.threshold,
        )
    except RuntimeError as e:
        # Backend adapter connection or configuration error
        raise HTTPException(
            status_code=503,  # Service Unavailable
            detail=f"Backend '{query.backend}' is not available: {str(e)}",
        )

    pending_item_id = None

    # Convert candidates to MatchCandidate objects
    from app.models import MatchCandidate

    match_candidates = [
        MatchCandidate(product_id=product_id, confidence=confidence)
        for product_id, confidence in candidates
    ]

    # If successful match, log it for reference
    if success and candidates:
        best_match = candidates[0]
        match_log = MatchLog(
            original_text=query.text,
            normalized_text=normalized_input,
            language=language,
            matched_product_id=best_match[0],  # product_id
            matched_text="",  # We don't track this anymore
            confidence_score=best_match[1],  # confidence
            threshold_used=query.threshold,
            owner_id=current_user.id,
        )
        session.add(match_log)
        session.commit()
    else:
        # If no match or low confidence, optionally add to pending queue
        if query.create_pending:
            pending_manager = PendingQueueManager(session)
            pending_query = pending_manager.add_to_pending(
                original_text=query.text,
                normalized_text=normalized_input,
                owner_id=current_user.id,
                backend=query.backend,
                candidates=candidates,
            )
            pending_item_id = pending_query.id

    return MatchResult(
        success=success,
        normalized_input=normalized_input,
        pending_query_id=pending_item_id,
        candidates=match_candidates,
        debug_info=debug_info,
    )


@router.get("/pending", response_model=PendingQueriesPublic)
def get_pending_queries(
    session: SessionDep,
    current_user: CurrentUser,
    status: str = "pending",
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    Get pending queries for manual resolution.
    """
    pending_manager = PendingQueueManager(session)

    pending_queries = pending_manager.get_pending_queries(
        owner_id=current_user.id, status=status, limit=limit, offset=skip
    )

    count = pending_manager.get_pending_count(current_user.id, status)

    # Convert to public models
    public_queries = []
    for query in pending_queries:
        public_query = PendingQueryPublic(
            id=query.id,
            original_text=query.original_text,
            normalized_text=query.normalized_text,
            candidates=query.candidates,
            status=query.status,
            backend=query.backend,
            created_at=query.created_at,
            owner_id=query.owner_id,
        )
        public_queries.append(public_query)

    return PendingQueriesPublic(data=public_queries, count=count)


@router.post("/resolve", response_model=Message)
def resolve_pending_query(
    *, session: SessionDep, current_user: CurrentUser, resolve_data: ResolveRequest
) -> Any:
    """
    Resolve a pending query by assigning it to a product or creating a new one.
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Resolve request received: {resolve_data}")

    try:
        pending_manager = PendingQueueManager(session)
        logger.info("PendingQueueManager created successfully")

        # Validate the request based on action
        logger.info(f"Validating action: {resolve_data.action}")
        if resolve_data.action == "assign" and not resolve_data.product_id:
            logger.error("Missing product_id for assign action")
            raise HTTPException(
                status_code=400, detail="product_id is required for assign action"
            )
        logger.info("Action validation passed")

        # Verify the pending query belongs to the current user
        logger.info(f"Looking up pending query: {resolve_data.pending_query_id}")
        pending_query = session.get(PendingQuery, resolve_data.pending_query_id)
        if not pending_query:
            logger.error(f"Pending query not found: {resolve_data.pending_query_id}")
            raise HTTPException(
                status_code=404, detail="Pending query not found or access denied"
            )

        if pending_query.owner_id != current_user.id:
            logger.error(
                f"Access denied for pending query: {resolve_data.pending_query_id}, owner: {pending_query.owner_id}, user: {current_user.id}"
            )
            raise HTTPException(
                status_code=404, detail="Pending query not found or access denied"
            )

        logger.info(f"Pending query found and verified: {pending_query.id}")

        logger.info("Calling resolve_pending_query on manager")
        success, error_message = pending_manager.resolve_pending_query(
            pending_query_id=resolve_data.pending_query_id,
            action=resolve_data.action,
            product_id=resolve_data.product_id,
            custom_alias=resolve_data.custom_alias,
        )
        logger.info(
            f"resolve_pending_query returned: success={success}, error={error_message}"
        )

        if not success:
            logger.error(f"resolve_pending_query failed: {error_message}")
            raise HTTPException(
                status_code=400,
                detail=error_message
                or "Failed to resolve pending query. Check that it exists and belongs to you.",
            )

        logger.info("Resolve operation completed successfully")
        return Message(message="Pending query resolved successfully")

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in resolve endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/pending/{pending_query_id}")
def delete_pending_query(
    session: SessionDep, current_user: CurrentUser, pending_query_id: uuid.UUID
) -> Message:
    """
    Delete a pending query without resolving it.
    """
    pending_manager = PendingQueueManager(session)

    success = pending_manager.delete_pending_query(
        pending_query_id=pending_query_id, owner_id=current_user.id
    )

    if not success:
        raise HTTPException(
            status_code=404, detail="Pending query not found or access denied"
        )

    return Message(message="Pending query deleted successfully")


@router.get("/external-products")
def get_external_products(backend: str = "mock") -> Any:
    """
    Get external products from the specified backend adapter.
    """
    # Get specified backend from registry
    adapter = get_backend(backend)

    # Get all external products
    external_products = adapter.get_all_products()

    return {
        "data": external_products,
        "count": len(external_products),
        "backend": backend,
    }


@router.get("/backends")
def get_available_backends() -> list[BackendInfo]:
    """
    Get list of available backend adapters with descriptions.
    """
    from app.config.loader import load_backends_config

    config = load_backends_config()
    backends = config.get("backends", {})

    return [
        BackendInfo(name=name, description=backend_config.get("description", name))
        for name, backend_config in backends.items()
    ]


@router.get("/languages")
def get_available_languages() -> Any:
    """
    Get list of supported languages for matching.
    """
    from app.services.normalization.base import get_available_languages

    languages = get_available_languages()
    return languages


@router.get("/stats")
def get_matching_stats(
    session: SessionDep, current_user: CurrentUser, backend: str = "mock"
) -> Any:
    """
    Get matching statistics for the user.
    """
    pending_manager = PendingQueueManager(session)

    # Get specified backend from registry
    adapter = get_backend(backend)

    pending_count = pending_manager.get_pending_count(current_user.id, "pending")
    resolved_count = pending_manager.get_pending_count(current_user.id, "resolved")
    ignored_count = pending_manager.get_pending_count(current_user.id, "ignored")

    # Get match log count
    from sqlmodel import func, select

    match_log_count = session.exec(
        select(func.count())
        .select_from(MatchLog)
        .where(MatchLog.owner_id == current_user.id)
    ).one()

    # Get stats from external system
    external_products = adapter.get_all_products()
    total_products = len(external_products)

    return {
        "total_products": total_products,
        "successful_matches": match_log_count,
        "pending_queries": pending_count,
        "resolved_queries": resolved_count,
        "ignored_queries": ignored_count,
    }


@router.get("/settings", response_model=GlobalSettings)
def get_matching_settings() -> GlobalSettings:
    """
    Get global matching settings from configuration.
    """
    settings = get_global_settings()
    return GlobalSettings(
        default_threshold=settings.get("default_threshold", 0.8),
        max_candidates=settings.get("max_candidates", 5),
    )
