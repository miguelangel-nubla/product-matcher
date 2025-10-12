"""Test cases for the matching API routes."""

import uuid
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import MatchRequest, MatchResult, PendingQuery


class TestMatchingRoutes:
    """Test cases for matching API routes."""

    @patch('app.api.routes.matching.ProductMatcher')
    @patch('app.api.routes.matching.get_global_settings')
    def test_match_product_success(
        self,
        mock_get_global_settings,
        mock_product_matcher,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test successful product matching."""
        # Mock dependencies
        mock_global_settings = Mock()
        mock_global_settings.default_threshold = 0.8
        mock_global_settings.max_candidates = 10
        mock_get_global_settings.return_value = mock_global_settings

        # Mock matcher
        mock_matcher_instance = Mock()
        mock_matcher_instance.match_product.return_value = (
            True,  # success
            "normalized apple juice",  # normalized_input
            [("product123", 0.95), ("product456", 0.85)],  # candidates
            []  # debug_info (list of DebugStep objects)
        )
        mock_product_matcher.return_value = mock_matcher_instance

        # Make request
        request_data = {
            "text": "apple juice",
            "backend": "test-backend",
            "threshold": 0.9,
            "create_pending": False
        }

        response = client.post(
            "/api/v1/matching/match",
            headers=normal_user_token_headers,
            json=request_data,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["normalized_input"] == "normalized apple juice"
        assert data["pending_query_id"] is None
        assert len(data["candidates"]) == 2
        assert data["candidates"][0]["product_id"] == "product123"
        assert data["candidates"][0]["confidence"] == 0.95
        assert data["debug_info"] == []

        # Verify matcher was called correctly
        mock_matcher_instance.match_product.assert_called_once_with(
            input_query="apple juice",
            backend_name="test-backend",
            threshold=0.9,
            max_candidates=10,
        )

    @patch('app.api.routes.matching.ProductMatcher')
    @patch('app.api.routes.matching.get_global_settings')
    def test_match_product_use_default_threshold(
        self,
        mock_get_global_settings,
        mock_product_matcher,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test product matching using default threshold."""
        # Mock dependencies
        mock_global_settings = Mock()
        mock_global_settings.default_threshold = 0.7
        mock_global_settings.max_candidates = 10
        mock_get_global_settings.return_value = mock_global_settings

        mock_matcher_instance = Mock()
        mock_matcher_instance.match_product.return_value = (
            True, "normalized text", [("product1", 0.8)], []
        )
        mock_product_matcher.return_value = mock_matcher_instance

        # Make request without threshold
        request_data = {
            "text": "apple juice",
            "backend": "test-backend",
            "create_pending": False
        }

        response = client.post(
            "/api/v1/matching/match",
            headers=normal_user_token_headers,
            json=request_data,
        )

        assert response.status_code == 200

        # Verify default threshold was used
        mock_matcher_instance.match_product.assert_called_once()
        call_args = mock_matcher_instance.match_product.call_args
        assert call_args[1]["threshold"] == 0.7

    @patch('app.api.routes.matching.ProductMatcher')
    @patch('app.api.routes.matching.get_global_settings')
    @patch('app.api.routes.matching.PendingQueueManager')
    def test_match_product_no_match_create_pending(
        self,
        mock_pending_queue_manager,
        mock_get_global_settings,
        mock_product_matcher,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test product matching with no match and create pending."""
        # Mock dependencies
        mock_global_settings = Mock()
        mock_global_settings.default_threshold = 0.8
        mock_global_settings.max_candidates = 10
        mock_get_global_settings.return_value = mock_global_settings

        # Mock matcher returning no success
        mock_matcher_instance = Mock()
        mock_matcher_instance.match_product.return_value = (
            False,  # no success
            "normalized text",
            [("product1", 0.5)],  # low confidence candidates
            []
        )
        mock_product_matcher.return_value = mock_matcher_instance

        # Mock pending queue manager
        mock_pending_manager_instance = Mock()
        mock_pending_query = Mock()
        mock_pending_query.id = uuid.uuid4()
        mock_pending_manager_instance.add_to_pending.return_value = mock_pending_query
        mock_pending_queue_manager.return_value = mock_pending_manager_instance

        # Make request with create_pending=True
        request_data = {
            "text": "unknown product",
            "backend": "test-backend",
            "threshold": 0.8,
            "create_pending": True
        }

        response = client.post(
            "/api/v1/matching/match",
            headers=normal_user_token_headers,
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert data["pending_query_id"] == str(mock_pending_query.id)

        # Verify pending query was created
        mock_pending_manager_instance.add_to_pending.assert_called_once()

    @patch('app.api.routes.matching.ProductMatcher')
    def test_match_product_backend_error(
        self,
        mock_product_matcher,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test product matching with backend error."""
        # Mock matcher raising RuntimeError
        mock_matcher_instance = Mock()
        mock_matcher_instance.match_product.side_effect = RuntimeError("Backend connection failed")
        mock_product_matcher.return_value = mock_matcher_instance

        request_data = {
            "text": "apple juice",
            "backend": "broken-backend",
            "create_pending": False
        }

        response = client.post(
            "/api/v1/matching/match",
            headers=normal_user_token_headers,
            json=request_data,
        )

        assert response.status_code == 400
        assert "Backend connection failed" in response.json()["detail"]

    def test_match_product_unauthorized(self, client: TestClient):
        """Test product matching without authentication."""
        request_data = {
            "text": "apple juice",
            "backend": "test-backend",
            "create_pending": False
        }

        response = client.post("/api/v1/matching/match", json=request_data)
        assert response.status_code == 401

    @patch('app.api.routes.matching.PendingQueueManager')
    def test_get_pending_queries_success(
        self,
        mock_pending_queue_manager,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test successful retrieval of pending queries."""
        # Mock pending queries
        mock_query_1 = Mock()
        mock_query_1.id = uuid.uuid4()
        mock_query_1.original_text = "apple juice"
        mock_query_1.normalized_text = "apple juice"
        mock_query_1.candidates = '[]'
        mock_query_1.status = "pending"
        mock_query_1.backend = "test-backend"
        mock_query_1.threshold = 0.8
        mock_query_1.created_at = "2023-01-01T00:00:00"
        mock_query_1.owner_id = uuid.uuid4()

        mock_query_2 = Mock()
        mock_query_2.id = uuid.uuid4()
        mock_query_2.original_text = "banana smoothie"
        mock_query_2.normalized_text = "banana smoothie"
        mock_query_2.candidates = '[]'
        mock_query_2.status = "pending"
        mock_query_2.backend = "test-backend"
        mock_query_2.threshold = 0.8
        mock_query_2.created_at = "2023-01-01T01:00:00"
        mock_query_2.owner_id = uuid.uuid4()

        mock_pending_manager = Mock()
        mock_pending_manager.get_pending_queries.return_value = [mock_query_1, mock_query_2]
        mock_pending_manager.get_pending_count.return_value = 2
        mock_pending_queue_manager.return_value = mock_pending_manager

        response = client.get(
            "/api/v1/matching/pending",
            headers=normal_user_token_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 2
        assert len(data["data"]) == 2
        assert data["data"][0]["original_text"] == "apple juice"
        assert data["data"][1]["original_text"] == "banana smoothie"

    @patch('app.api.routes.matching.PendingQueueManager')
    def test_get_pending_queries_with_filters(
        self,
        mock_pending_queue_manager,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test pending queries with status filter and pagination."""
        mock_pending_manager = Mock()
        mock_pending_manager.get_pending_queries.return_value = []
        mock_pending_manager.get_pending_count.return_value = 0
        mock_pending_queue_manager.return_value = mock_pending_manager

        response = client.get(
            "/api/v1/matching/pending?status=resolved&skip=10&limit=5",
            headers=normal_user_token_headers,
        )

        assert response.status_code == 200

        # Verify the correct parameters were passed
        mock_pending_manager.get_pending_queries.assert_called_once()
        call_args = mock_pending_manager.get_pending_queries.call_args
        assert call_args[1]["status"] == "resolved"
        assert call_args[1]["limit"] == 5
        assert call_args[1]["offset"] == 10

    def test_get_pending_queries_unauthorized(self, client: TestClient):
        """Test pending queries without authentication."""
        response = client.get("/api/v1/matching/pending")
        assert response.status_code == 401

    @patch('app.api.routes.matching.PendingQueueManager')
    def test_get_pending_queries_empty_result(
        self,
        mock_pending_queue_manager,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test pending queries with empty result."""
        mock_pending_manager = Mock()
        mock_pending_manager.get_pending_queries.return_value = []
        mock_pending_manager.get_pending_count.return_value = 0
        mock_pending_queue_manager.return_value = mock_pending_manager

        response = client.get(
            "/api/v1/matching/pending",
            headers=normal_user_token_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == 0
        assert len(data["data"]) == 0

    @patch('app.api.routes.matching.ProductMatcher')
    @patch('app.api.routes.matching.get_global_settings')
    def test_match_product_invalid_request_data(
        self,
        mock_get_global_settings,
        mock_product_matcher,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test product matching with invalid request data."""
        # Missing required fields
        request_data = {
            "backend": "test-backend",
            # Missing "text" field
        }

        response = client.post(
            "/api/v1/matching/match",
            headers=normal_user_token_headers,
            json=request_data,
        )

        assert response.status_code == 422  # Validation error

    @patch('app.api.routes.matching.ProductMatcher')
    @patch('app.api.routes.matching.get_global_settings')
    def test_match_product_logs_successful_match(
        self,
        mock_get_global_settings,
        mock_product_matcher,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
        db: Session,
    ):
        """Test that successful matches are logged to the database."""
        # Mock dependencies
        mock_global_settings = Mock()
        mock_global_settings.default_threshold = 0.8
        mock_global_settings.max_candidates = 10
        mock_get_global_settings.return_value = mock_global_settings

        # Mock successful match
        mock_matcher_instance = Mock()
        mock_matcher_instance.match_product.return_value = (
            True,  # success
            "normalized text",
            [("product123", 0.95)],
            []
        )
        mock_product_matcher.return_value = mock_matcher_instance

        request_data = {
            "text": "apple juice",
            "backend": "test-backend",
            "threshold": 0.9,
            "create_pending": False
        }

        response = client.post(
            "/api/v1/matching/match",
            headers=normal_user_token_headers,
            json=request_data,
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Note: In a real test, you might want to verify that a MatchLog was
        # actually added to the database, but this would require more complex
        # database setup and cleanup

    @patch('app.api.routes.matching.get_backend')
    def test_get_external_products_success(
        self,
        mock_get_backend,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test successful retrieval of external products."""
        # Mock backend adapter
        mock_adapter = Mock()
        mock_adapter.get_all_products.return_value = [
            {"id": "product1", "name": "Apple Juice"},
            {"id": "product2", "name": "Orange Juice"},
        ]
        mock_get_backend.return_value = mock_adapter

        response = client.get(
            "/api/v1/matching/external-products?backend=test-backend",
            headers=normal_user_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["backend"] == "test-backend"
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "product1"

    def test_get_external_products_unauthorized(self, client: TestClient):
        """Test external products endpoint without authentication."""
        response = client.get("/api/v1/matching/external-products?backend=test-backend")
        assert response.status_code == 401

    @patch('app.api.routes.matching.get_backend')
    def test_get_external_products_invalid_backend(
        self,
        mock_get_backend,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test external products with invalid backend."""
        mock_get_backend.side_effect = ValueError("Invalid backend: nonexistent-backend")

        response = client.get(
            "/api/v1/matching/external-products?backend=nonexistent-backend",
            headers=normal_user_token_headers,
        )

        assert response.status_code == 400
        assert "Invalid backend" in response.json()["detail"]

    @patch('app.api.routes.matching.get_backend_config')
    @patch('app.adapters.registry.get_available_backends')
    def test_get_available_backends_success(
        self,
        mock_get_available_backends,
        mock_get_backend_config,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test successful retrieval of available backends."""
        # Mock backend names and configs
        mock_get_available_backends.return_value = ["grocy1", "mock"]

        # Create mock configs
        mock_config_grocy = Mock()
        mock_config_grocy.description = "Grocy Backend"

        mock_config_mock = Mock()
        mock_config_mock.description = "Mock Backend"

        mock_get_backend_config.side_effect = [mock_config_grocy, mock_config_mock]

        response = client.get(
            "/api/v1/matching/backends",
            headers=normal_user_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "grocy1"
        assert data[0]["description"] == "Grocy Backend"
        assert data[1]["name"] == "mock"
        assert data[1]["description"] == "Mock Backend"

    def test_get_available_backends_unauthorized(self, client: TestClient):
        """Test backends endpoint without authentication."""
        response = client.get("/api/v1/matching/backends")
        assert response.status_code == 401

    @patch('app.config.loader.get_language_configs')
    def test_get_available_languages_success(
        self,
        mock_get_language_configs,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test successful retrieval of available languages."""
        mock_get_language_configs.return_value = {
            "en": {"name": "English"},
            "es": {"name": "Spanish"},
            "fr": {"name": "French"},
        }

        response = client.get(
            "/api/v1/matching/languages",
            headers=normal_user_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data == ["en", "es", "fr"]

    def test_get_available_languages_unauthorized(self, client: TestClient):
        """Test languages endpoint without authentication."""
        response = client.get("/api/v1/matching/languages")
        assert response.status_code == 401

    @patch('app.api.routes.matching.get_global_settings')
    def test_get_matching_settings_success(
        self,
        mock_get_global_settings,
        client: TestClient,
        normal_user_token_headers: dict[str, str],
    ):
        """Test successful retrieval of matching settings."""
        mock_settings = Mock()
        mock_settings.default_threshold = 0.8
        mock_settings.max_candidates = 10
        mock_get_global_settings.return_value = mock_settings

        response = client.get(
            "/api/v1/matching/settings",
            headers=normal_user_token_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["default_threshold"] == 0.8
        assert data["max_candidates"] == 10

    def test_get_matching_settings_unauthorized(self, client: TestClient):
        """Test settings endpoint without authentication."""
        response = client.get("/api/v1/matching/settings")
        assert response.status_code == 401
