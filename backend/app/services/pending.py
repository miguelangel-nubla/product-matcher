"""
Pending queries queue management service.
"""

import uuid
from datetime import datetime, timezone

from sqlmodel import Session, desc, select

from app.models import PendingQuery


class PendingQueueManager:
    """
    Manages the pending queries queue for unmatched or low-confidence matches.
    """

    def __init__(self, session: Session):
        self.session = session

    def add_to_pending(
        self,
        original_text: str,
        normalized_text: str,
        owner_id: uuid.UUID,
        backend: str,
        threshold: float,
        candidates: list[tuple[str, float]] | None = None,
    ) -> PendingQuery:
        """
        Add a query to the pending queue.

        Args:
            original_text: Original input text
            normalized_text: Normalized version of the text
            owner_id: ID of the owner
            backend: Backend instance name that was used for matching
            threshold: Threshold that was used for matching
            candidates: List of (product_id, confidence) tuples from matching

        Returns:
            Created PendingQuery
        """
        import json

        # Convert candidates to JSON string
        candidates_json = None
        if candidates:
            candidates_json = json.dumps(
                [{"product_id": pid, "confidence": conf} for pid, conf in candidates]
            )

        existing_query_statement = select(PendingQuery).where(
            PendingQuery.owner_id == owner_id,
            PendingQuery.status == "pending",
            PendingQuery.original_text == original_text,
            PendingQuery.backend == backend,
            PendingQuery.threshold == threshold,
        )
        existing_query = self.session.exec(existing_query_statement).first()

        if existing_query:
            existing_query.normalized_text = normalized_text
            existing_query.candidates = candidates_json
            existing_query.backend = backend
            existing_query.threshold = threshold
            existing_query.created_at = datetime.now(timezone.utc)
            self.session.add(existing_query)
            self.session.commit()
            self.session.refresh(existing_query)
            return existing_query

        pending_query = PendingQuery(
            original_text=original_text,
            normalized_text=normalized_text,
            candidates=candidates_json,
            backend=backend,
            threshold=threshold,
            owner_id=owner_id,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(pending_query)
        self.session.commit()
        self.session.refresh(pending_query)

        return pending_query

    def get_pending_queries(
        self,
        owner_id: uuid.UUID,
        status: str = "pending",
        limit: int = 50,
        offset: int = 0,
    ) -> list[PendingQuery]:
        """
        Get pending queries for a user.

        Args:
            owner_id: ID of the owner
            status: Status filter (pending, resolved, ignored)
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            List of PendingQuery objects
        """
        statement = (
            select(PendingQuery)
            .where(PendingQuery.owner_id == owner_id, PendingQuery.status == status)
            .order_by(desc(PendingQuery.created_at))
            .offset(offset)
            .limit(limit)
        )

        return list(self.session.exec(statement).all())

    def resolve_pending_query(
        self,
        pending_query_id: uuid.UUID,
        action: str,
        product_id: str | None = None,
        custom_alias: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Resolve a pending query by assigning it to an external product or ignoring it.

        Args:
            pending_query_id: ID of the pending query
            action: Action to take ('assign', 'ignore')
            product_id: External product ID (for 'assign' action)
            custom_alias: Custom alias text to use instead of normalized text

        Returns:
            Tuple of (success, error_message)
        """
        import logging

        logger = logging.getLogger(__name__)

        logger.info(
            f"Starting resolve_pending_query: {pending_query_id}, action: {action}, product_id: {product_id}"
        )

        # Get the pending query
        pending_query = self.session.get(PendingQuery, pending_query_id)
        if not pending_query:
            error_msg = f"Pending query {pending_query_id} not found"
            logger.error(error_msg)
            return False, error_msg

        logger.info(
            f"Found pending query: {pending_query.original_text}, status: {pending_query.status}"
        )

        try:
            if action == "assign":
                if not product_id:
                    error_msg = "Product ID is required for assign action"
                    logger.error(error_msg)
                    return False, error_msg

                logger.info(f"Attempting to assign to product {product_id}")

                # Get the backend adapter and add the alias to the external system
                from app.adapters.registry import get_backend

                try:
                    adapter = get_backend(pending_query.backend)
                    logger.info(f"Got backend adapter: {pending_query.backend}")

                    # Use custom_alias if provided, otherwise use normalized_text
                    alias_to_add = (
                        custom_alias if custom_alias else pending_query.normalized_text
                    )
                    logger.info(
                        f"Adding alias '{alias_to_add}' to product {product_id}"
                    )

                    # Add the alias to the external product
                    alias_added, alias_error = adapter.add_alias(
                        product_id, alias_to_add
                    )
                    logger.info(
                        f"Alias addition result: success={alias_added}, error={alias_error}"
                    )

                    if not alias_added:
                        error_msg = (
                            alias_error
                            or f"Failed to add alias to external product {product_id}"
                        )
                        logger.error(error_msg)
                        return False, error_msg

                except Exception as e:
                    error_msg = f"Error adding alias to external system: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    return False, error_msg

                # Mark as resolved only after successfully adding the alias
                pending_query.status = "resolved"
                logger.info("Updated pending query status to resolved")

            elif action == "ignore":
                logger.info("Setting status to ignored")
                pending_query.status = "ignored"

            else:
                error_msg = f"Invalid action: {action}"
                logger.error(error_msg)
                return False, error_msg

            logger.info("Committing transaction")
            self.session.commit()
            logger.info("Transaction committed successfully")
            return True, None

        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            logger.error(f"Exception in resolve_pending_query: {e}", exc_info=True)
            self.session.rollback()
            return False, error_msg

    def get_pending_count(self, owner_id: uuid.UUID, status: str = "pending") -> int:
        """
        Get count of pending queries for a user.

        Args:
            owner_id: ID of the owner
            status: Status filter

        Returns:
            Count of pending queries
        """
        statement = select(PendingQuery).where(
            PendingQuery.owner_id == owner_id, PendingQuery.status == status
        )
        return len(self.session.exec(statement).all())

    def delete_pending_query(
        self, pending_query_id: uuid.UUID, owner_id: uuid.UUID
    ) -> bool:
        """
        Delete a pending query.

        Args:
            pending_query_id: ID of the pending query
            owner_id: ID of the owner (for security)

        Returns:
            True if successful, False otherwise
        """
        pending_query = self.session.get(PendingQuery, pending_query_id)
        if not pending_query or pending_query.owner_id != owner_id:
            return False

        self.session.delete(pending_query)
        self.session.commit()
        return True
