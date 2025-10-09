"""Test cases for the pending query management service."""

import uuid
import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from sqlmodel import Session

from app.services.pending import PendingQueueManager
from app.models import PendingQuery


class TestPendingQueueManager:
    """Test cases for PendingQueueManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.manager = PendingQueueManager(self.mock_session)
        self.test_owner_id = uuid.uuid4()
        self.test_pending_id = uuid.uuid4()

    def test_init(self):
        """Test manager initialization."""
        assert self.manager.session == self.mock_session

    def test_add_to_pending_without_candidates(self):
        """Test adding a query to pending without candidates."""
        original_text = "apple juice"
        normalized_text = "apple juice"
        backend = "test-backend"
        threshold = 0.8

        # Mock the database operations
        created_query = PendingQuery(
            id=self.test_pending_id,
            original_text=original_text,
            normalized_text=normalized_text,
            candidates=None,
            backend=backend,
            threshold=threshold,
            owner_id=self.test_owner_id,
            created_at=datetime.now().isoformat(),
            status="pending"
        )

        self.mock_session.add.return_value = None
        self.mock_session.commit.return_value = None
        self.mock_session.refresh.return_value = None

        with patch('app.services.pending.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00"

            # Execute
            result = self.manager.add_to_pending(
                original_text=original_text,
                normalized_text=normalized_text,
                owner_id=self.test_owner_id,
                backend=backend,
                threshold=threshold
            )

            # Verify session operations
            self.mock_session.add.assert_called_once()
            self.mock_session.commit.assert_called_once()
            self.mock_session.refresh.assert_called_once()

            # Verify the created query
            added_query = self.mock_session.add.call_args[0][0]
            assert added_query.original_text == original_text
            assert added_query.normalized_text == normalized_text
            assert added_query.candidates is None
            assert added_query.backend == backend
            assert added_query.threshold == threshold
            assert added_query.owner_id == self.test_owner_id

    def test_add_to_pending_with_candidates(self):
        """Test adding a query to pending with candidates."""
        original_text = "apple juice"
        normalized_text = "apple juice"
        backend = "test-backend"
        threshold = 0.8
        candidates = [("product1", 0.7), ("product2", 0.6)]

        expected_candidates_json = json.dumps([
            {"product_id": "product1", "confidence": 0.7},
            {"product_id": "product2", "confidence": 0.6}
        ])

        self.mock_session.add.return_value = None
        self.mock_session.commit.return_value = None
        self.mock_session.refresh.return_value = None

        with patch('app.services.pending.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00"

            # Execute
            result = self.manager.add_to_pending(
                original_text=original_text,
                normalized_text=normalized_text,
                owner_id=self.test_owner_id,
                backend=backend,
                threshold=threshold,
                candidates=candidates
            )

            # Verify the candidates JSON
            added_query = self.mock_session.add.call_args[0][0]
            assert added_query.candidates == expected_candidates_json

    def test_get_pending_queries(self):
        """Test retrieving pending queries."""
        mock_queries = [
            PendingQuery(
                id=uuid.uuid4(),
                original_text="apple juice",
                normalized_text="apple juice",
                owner_id=self.test_owner_id,
                backend="test",
                threshold=0.8,
                status="pending",
                created_at="2023-01-01T00:00:00"
            ),
            PendingQuery(
                id=uuid.uuid4(),
                original_text="banana smoothie",
                normalized_text="banana smoothie",
                owner_id=self.test_owner_id,
                backend="test",
                threshold=0.8,
                status="pending",
                created_at="2023-01-01T01:00:00"
            )
        ]

        mock_exec_result = Mock()
        mock_exec_result.all.return_value = mock_queries
        self.mock_session.exec.return_value = mock_exec_result

        # Execute
        result = self.manager.get_pending_queries(
            owner_id=self.test_owner_id,
            status="pending",
            limit=10,
            offset=0
        )

        # Verify
        assert len(result) == 2
        assert result == mock_queries
        self.mock_session.exec.assert_called_once()

    def test_get_pending_queries_with_filters(self):
        """Test retrieving pending queries with custom filters."""
        mock_queries = []
        mock_exec_result = Mock()
        mock_exec_result.all.return_value = mock_queries
        self.mock_session.exec.return_value = mock_exec_result

        # Execute with custom parameters
        result = self.manager.get_pending_queries(
            owner_id=self.test_owner_id,
            status="resolved",
            limit=5,
            offset=10
        )

        # Verify
        assert result == []
        self.mock_session.exec.assert_called_once()

    @patch('app.adapters.registry.get_backend')
    def test_resolve_pending_query_assign_success(self, mock_get_backend):
        """Test successfully resolving a pending query with assign action."""
        # Mock pending query
        mock_pending_query = Mock()
        mock_pending_query.backend = "test-backend"
        mock_pending_query.normalized_text = "apple juice"
        mock_pending_query.original_text = "apple juice"
        mock_pending_query.status = "pending"

        self.mock_session.get.return_value = mock_pending_query

        # Mock backend adapter
        mock_adapter = Mock()
        mock_adapter.add_alias.return_value = (True, None)
        mock_get_backend.return_value = mock_adapter

        # Execute
        success, error = self.manager.resolve_pending_query(
            pending_query_id=self.test_pending_id,
            action="assign",
            product_id="product123"
        )

        # Verify
        assert success is True
        assert error is None
        assert mock_pending_query.status == "resolved"
        self.mock_session.get.assert_called_once_with(PendingQuery, self.test_pending_id)
        mock_get_backend.assert_called_once_with("test-backend")
        mock_adapter.add_alias.assert_called_once_with("product123", "apple juice")
        self.mock_session.commit.assert_called_once()

    @patch('app.adapters.registry.get_backend')
    def test_resolve_pending_query_assign_with_custom_alias(self, mock_get_backend):
        """Test resolving pending query with custom alias."""
        mock_pending_query = Mock()
        mock_pending_query.backend = "test-backend"
        mock_pending_query.normalized_text = "apple juice"
        mock_pending_query.status = "pending"

        self.mock_session.get.return_value = mock_pending_query

        mock_adapter = Mock()
        mock_adapter.add_alias.return_value = (True, None)
        mock_get_backend.return_value = mock_adapter

        # Execute with custom alias
        success, error = self.manager.resolve_pending_query(
            pending_query_id=self.test_pending_id,
            action="assign",
            product_id="product123",
            custom_alias="custom apple juice"
        )

        # Verify custom alias was used
        mock_adapter.add_alias.assert_called_once_with("product123", "custom apple juice")

    def test_resolve_pending_query_ignore(self):
        """Test resolving a pending query with ignore action."""
        mock_pending_query = Mock()
        mock_pending_query.status = "pending"

        self.mock_session.get.return_value = mock_pending_query

        # Execute
        success, error = self.manager.resolve_pending_query(
            pending_query_id=self.test_pending_id,
            action="ignore"
        )

        # Verify
        assert success is True
        assert error is None
        assert mock_pending_query.status == "ignored"
        self.mock_session.commit.assert_called_once()

    def test_resolve_pending_query_not_found(self):
        """Test resolving a non-existent pending query."""
        self.mock_session.get.return_value = None

        # Execute
        success, error = self.manager.resolve_pending_query(
            pending_query_id=self.test_pending_id,
            action="assign",
            product_id="product123"
        )

        # Verify
        assert success is False
        assert "not found" in error

    def test_resolve_pending_query_assign_without_product_id(self):
        """Test resolving with assign action but no product ID."""
        mock_pending_query = Mock()
        self.mock_session.get.return_value = mock_pending_query

        # Execute
        success, error = self.manager.resolve_pending_query(
            pending_query_id=self.test_pending_id,
            action="assign"
        )

        # Verify
        assert success is False
        assert "Product ID is required" in error

    @patch('app.adapters.registry.get_backend')
    def test_resolve_pending_query_assign_alias_failure(self, mock_get_backend):
        """Test resolving pending query when alias addition fails."""
        mock_pending_query = Mock()
        mock_pending_query.backend = "test-backend"
        mock_pending_query.normalized_text = "apple juice"
        mock_pending_query.status = "pending"

        self.mock_session.get.return_value = mock_pending_query

        # Mock adapter failure
        mock_adapter = Mock()
        mock_adapter.add_alias.return_value = (False, "External system error")
        mock_get_backend.return_value = mock_adapter

        # Execute
        success, error = self.manager.resolve_pending_query(
            pending_query_id=self.test_pending_id,
            action="assign",
            product_id="product123"
        )

        # Verify
        assert success is False
        assert "External system error" in error

    def test_resolve_pending_query_invalid_action(self):
        """Test resolving pending query with invalid action."""
        mock_pending_query = Mock()
        self.mock_session.get.return_value = mock_pending_query

        # Execute
        success, error = self.manager.resolve_pending_query(
            pending_query_id=self.test_pending_id,
            action="invalid_action"
        )

        # Verify
        assert success is False
        assert "Invalid action" in error

    @patch('app.adapters.registry.get_backend')
    def test_resolve_pending_query_database_exception(self, mock_get_backend):
        """Test resolving pending query with database exception."""
        mock_pending_query = Mock()
        mock_pending_query.backend = "test-backend"
        mock_pending_query.normalized_text = "apple juice"
        mock_pending_query.status = "pending"

        self.mock_session.get.return_value = mock_pending_query
        self.mock_session.commit.side_effect = Exception("Database error")

        mock_adapter = Mock()
        mock_adapter.add_alias.return_value = (True, None)
        mock_get_backend.return_value = mock_adapter

        # Execute
        success, error = self.manager.resolve_pending_query(
            pending_query_id=self.test_pending_id,
            action="assign",
            product_id="product123"
        )

        # Verify
        assert success is False
        assert "Database error" in error
        self.mock_session.rollback.assert_called_once()

    def test_get_pending_count(self):
        """Test getting count of pending queries."""
        mock_queries = [Mock(), Mock(), Mock()]  # 3 queries
        mock_exec_result = Mock()
        mock_exec_result.all.return_value = mock_queries
        self.mock_session.exec.return_value = mock_exec_result

        # Execute
        count = self.manager.get_pending_count(
            owner_id=self.test_owner_id,
            status="pending"
        )

        # Verify
        assert count == 3
        self.mock_session.exec.assert_called_once()

    def test_delete_pending_query_success(self):
        """Test successfully deleting a pending query."""
        mock_pending_query = Mock()
        mock_pending_query.owner_id = self.test_owner_id

        self.mock_session.get.return_value = mock_pending_query

        # Execute
        result = self.manager.delete_pending_query(
            pending_query_id=self.test_pending_id,
            owner_id=self.test_owner_id
        )

        # Verify
        assert result is True
        self.mock_session.delete.assert_called_once_with(mock_pending_query)
        self.mock_session.commit.assert_called_once()

    def test_delete_pending_query_not_found(self):
        """Test deleting a non-existent pending query."""
        self.mock_session.get.return_value = None

        # Execute
        result = self.manager.delete_pending_query(
            pending_query_id=self.test_pending_id,
            owner_id=self.test_owner_id
        )

        # Verify
        assert result is False
        self.mock_session.delete.assert_not_called()

    def test_delete_pending_query_wrong_owner(self):
        """Test deleting a pending query with wrong owner."""
        mock_pending_query = Mock()
        mock_pending_query.owner_id = uuid.uuid4()  # Different owner

        self.mock_session.get.return_value = mock_pending_query

        # Execute
        result = self.manager.delete_pending_query(
            pending_query_id=self.test_pending_id,
            owner_id=self.test_owner_id
        )

        # Verify
        assert result is False
        self.mock_session.delete.assert_not_called()
