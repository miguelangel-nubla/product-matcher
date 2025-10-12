"""
Product matching API routes.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from app.adapters.registry import get_backend
from app.api.deps import CurrentUser, SessionDep
from app.config.loader import get_backend_config, get_global_settings
from app.models import (
    BackendInfo,
    GlobalSettings,
    MatchLog,
    MatchLogPublic,
    MatchLogsPublic,
    MatchRequest,
    MatchResult,
    Message,
    PendingQueriesPublic,
    PendingQuery,
    PendingQueryPublic,
    ResolveRequest,
)
from app.services.matcher.matcher import ProductMatcher
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
    # Initialize the refactored matcher
    matcher = ProductMatcher()

    # Get global settings and ensure valid threshold
    global_settings = get_global_settings()
    threshold = query.threshold or global_settings.default_threshold

    try:
        success, normalized_input, candidates, debug_info = matcher.match_product(
            input_query=query.text,
            backend_name=query.backend,
            threshold=threshold,
            max_candidates=global_settings.max_candidates,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
            backend=query.backend,
            matched_product_id=best_match[0],  # product_id
            matched_text="",  # We don't track this anymore
            confidence_score=best_match[1],  # confidence
            threshold_used=threshold,
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
                threshold=threshold,
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
            threshold=query.threshold,
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
def get_external_products(_current_user: CurrentUser, backend: str) -> Any:
    """
    Get external products from the specified backend adapter.
    """
    # Get specified backend from registry
    try:
        adapter = get_backend(backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid backend: {str(e)}")

    # Get all external products
    external_products = adapter.get_all_products()

    return {
        "data": external_products,
        "count": len(external_products),
        "backend": backend,
    }


@router.get("/backends")
def get_available_backends(_current_user: CurrentUser) -> list[BackendInfo]:
    """
    Get list of available backend adapters with descriptions.
    """
    from app.adapters.registry import get_available_backends

    backend_names = get_available_backends()

    return [
        BackendInfo(name=name, description=get_backend_config(name).description)
        for name in backend_names
    ]


@router.get("/languages")
def get_available_languages(_current_user: CurrentUser) -> Any:
    """
    Get list of supported languages for matching.
    """
    from app.config.loader import get_language_configs

    languages = list(get_language_configs().keys())
    return languages


@router.get("/stats")
def get_matching_stats(
    session: SessionDep, current_user: CurrentUser, backend: str
) -> Any:
    """
    Get matching statistics for the user.
    """
    pending_manager = PendingQueueManager(session)

    # Get specified backend from registry (just to validate it exists)
    try:
        adapter = get_backend(backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid backend: {str(e)}")

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
def get_matching_settings(_current_user: CurrentUser) -> GlobalSettings:
    """
    Get global matching settings from configuration.
    """
    settings = get_global_settings()
    return settings


@router.get("/logs", response_model=MatchLogsPublic)
def get_match_logs(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 50,
) -> Any:
    """
    Get match logs for the current user.
    """
    from sqlmodel import desc, func, select

    # Get match logs for the current user, sorted by timestamp (newest first)
    statement = (
        select(MatchLog)
        .where(MatchLog.owner_id == current_user.id)
        .order_by(desc(MatchLog.created_at))
        .offset(skip)
        .limit(limit)
    )

    match_logs = session.exec(statement).all()

    # Get total count
    count_statement = (
        select(func.count())
        .select_from(MatchLog)
        .where(MatchLog.owner_id == current_user.id)
    )
    count = session.exec(count_statement).one()

    # Convert to public models
    public_logs = []
    for log in match_logs:
        public_log = MatchLogPublic(
            id=log.id,
            original_text=log.original_text,
            normalized_text=log.normalized_text,
            backend=log.backend,
            matched_product_id=log.matched_product_id,
            matched_text=log.matched_text,
            confidence_score=log.confidence_score,
            threshold_used=log.threshold_used,
            created_at=log.created_at,
            owner_id=log.owner_id,
        )
        public_logs.append(public_log)

    return MatchLogsPublic(data=public_logs, count=count)
