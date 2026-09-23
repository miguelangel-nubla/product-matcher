"""Test cases for the DataPreparation service."""

from unittest.mock import Mock

import pytest

from app.adapters.base import ExternalProduct
from app.services.debug import DebugStepTracker
from app.services.matcher.context import MatchingContext
from app.services.matcher.data_preparation import DataPreparation


class TestDataPreparation:
    """Test cases for DataPreparation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.data_prep = DataPreparation()
        self.mock_backend = Mock()
        self.mock_backend.name = "mock"
        self.mock_backend.language = "en"
        self.mock_backend.adapter = Mock()
        self.debug = DebugStepTracker()

    def test_init(self):
        """Test DataPreparation initialization."""
        assert isinstance(self.data_prep, DataPreparation)

    def test_prepare_context_success(self):
        """Test successful context preparation."""
        # Mock normalizer
        mock_normalizer = Mock()
        mock_normalizer.normalize.side_effect = [
            ["apple", "juice"],  # For input normalization
            ["apple", "juice"],  # For alias 1
            ["orange", "juice"],  # For alias 2
        ]

        # Mock the _get_normalized_aliases method
        mock_aliases = [
            ("product1", "Apple Juice", ["apple", "juice"]),
            ("product2", "Orange Juice", ["orange", "juice"]),
        ]
        self.data_prep._get_normalized_aliases = Mock(return_value=mock_aliases)

        # Execute
        context = self.data_prep.prepare_context(
            mock_normalizer, "Apple Juice", self.mock_backend, self.debug
        )

        # Verify
        assert isinstance(context, MatchingContext)
        assert context.input_tokens == ["apple", "juice"]
        assert context.normalized_input == "apple juice"
        assert context.normalized_aliases == mock_aliases
        assert context.backend == self.mock_backend
        assert context.debug == self.debug

        # Verify normalizer was called for input
        mock_normalizer.normalize.assert_called_with("Apple Juice")

        # Verify debug information was added
        debug_steps = self.debug.get_debug_info()
        assert len(debug_steps) >= 2
        assert any("Starting data preparation" in step.message for step in debug_steps)
        assert any("Data preparation completed" in step.message for step in debug_steps)

    def test_prepare_context_empty_input(self):
        """Test context preparation with empty input."""
        mock_normalizer = Mock()
        mock_normalizer.normalize.return_value = []

        self.data_prep._get_normalized_aliases = Mock(return_value=[])

        context = self.data_prep.prepare_context(
            mock_normalizer, "", self.mock_backend, self.debug
        )

        assert context.input_tokens == []
        assert context.normalized_input == ""
        assert context.normalized_aliases == []

    def test_prepare_context_normalization_error(self):
        """Test context preparation when normalization fails."""
        mock_normalizer = Mock()
        mock_normalizer.normalize.side_effect = Exception("Normalization error")

        with pytest.raises(Exception, match="Normalization error"):
            self.data_prep.prepare_context(
                mock_normalizer, "test input", self.mock_backend, self.debug
            )

    def test_get_normalized_aliases_success(self):
        """Test successful alias normalization."""

        # Mock normalizer
        mock_normalizer = Mock()
        mock_normalizer.normalize.side_effect = [
            ["apple", "juice"],
            ["orange", "juice"],
            ["banana", "smoothie"],
        ]

        # Mock backend adapter
        self.mock_backend.adapter.get_all_aliases.return_value = [
            ("product1", "Apple Juice"),
            ("product2", "Orange Juice"),
            ("product3", "Banana Smoothie"),
        ]

        # Execute
        result = self.data_prep._get_normalized_aliases(
            mock_normalizer, self.debug, self.mock_backend.adapter
        )

        # Verify
        expected = [
            ("product1", "Apple Juice", ["apple", "juice"]),
            ("product2", "Orange Juice", ["orange", "juice"]),
            ("product3", "Banana Smoothie", ["banana", "smoothie"]),
        ]
        assert result == expected

        # Verify all aliases were normalized
        assert mock_normalizer.normalize.call_count == 3
        self.mock_backend.adapter.get_all_aliases.assert_called_once()

    def test_get_normalized_aliases_empty_backend(self):
        """Test alias normalization with empty backend."""
        self.mock_backend.adapter.get_all_aliases.return_value = []
        mock_normalizer = Mock()

        result = self.data_prep._get_normalized_aliases(
            mock_normalizer, self.debug, self.mock_backend.adapter
        )

        assert result == []
        mock_normalizer.normalize.assert_not_called()

    def test_get_normalized_aliases_normalization_error(self):
        """Test alias normalization with normalization error."""
        self.mock_backend.adapter.get_all_aliases.return_value = [("product1", "Test Product")]
        mock_normalizer = Mock()
        mock_normalizer.normalize.side_effect = Exception("Normalization failed")

        with pytest.raises(Exception, match="Normalization failed"):
            self.data_prep._get_normalized_aliases(
                mock_normalizer, self.debug, self.mock_backend.adapter
            )


    def test_prepare_context_filters_candidate_product_ids(self):
        """Constrained mode normalizes only shortlisted aliases/barcodes."""
        mock_normalizer = Mock()
        mock_normalizer.normalize.side_effect = [
            ["aceite", "vextra"],  # input
            ["aceite", "vextra"],  # alias 9
            ["aceite", "girasol"],  # alias 28
        ]
        self.mock_backend.adapter.get_all_aliases.return_value = [
            ("9", "aceite vextra"),
            ("365", "Aceite de sésamo"),
            ("28", "- Aceite de girasol"),
        ]
        p9 = Mock(id=9, barcodes=["8402001020629"], barcode=None)
        p365 = Mock(id=365, barcodes=["12345678"], barcode=None)
        p28 = Mock(id=28, barcodes=["87654321"], barcode=None)
        self.mock_backend.adapter.get_all_products.return_value = [p9, p365, p28]

        context = self.data_prep.prepare_context(
            mock_normalizer,
            "aceite v.extra",
            self.mock_backend,
            self.debug,
            candidate_product_ids={"9", "28"},
        )

        assert [row[0] for row in context.normalized_aliases] == ["9", "28"]
        assert set(context.barcodes) == {"9", "28"}
        # Input + two shortlisted aliases only (365 never normalized).
        assert mock_normalizer.normalize.call_count == 3
        assert mock_normalizer.normalize.call_args_list[1].args[0] == "aceite vextra"
        assert mock_normalizer.normalize.call_args_list[2].args[0] == "- Aceite de girasol"

    def test_get_normalized_aliases_filters_before_normalize(self):
        mock_normalizer = Mock()
        mock_normalizer.normalize.side_effect = [["aceite", "vextra"]]
        self.mock_backend.adapter.get_all_aliases.return_value = [
            ("9", "aceite vextra"),
            ("365", "Aceite de sésamo"),
        ]

        result = self.data_prep._get_normalized_aliases(
            mock_normalizer,
            self.debug,
            self.mock_backend.adapter,
            candidate_product_ids={"9"},
        )

        assert result == [("9", "aceite vextra", ["aceite", "vextra"])]
        mock_normalizer.normalize.assert_called_once_with("aceite vextra")

    def test_prepare_context_empty_candidate_list_matches_nothing(self):
        mock_normalizer = Mock()
        mock_normalizer.normalize.return_value = ["aceite"]
        self.mock_backend.adapter.get_all_aliases.return_value = [
            ("9", "aceite vextra"),
        ]
        self.mock_backend.adapter.get_all_products.return_value = [
            Mock(id=9, barcodes=["8402001020629"], barcode=None)
        ]

        context = self.data_prep.prepare_context(
            mock_normalizer,
            "aceite v.extra",
            self.mock_backend,
            self.debug,
            candidate_product_ids=set(),
        )

        assert context.normalized_aliases == []
        assert context.barcodes == {}
        mock_normalizer.normalize.assert_called_once_with("aceite v.extra")

    def test_clear_cache(self):
        """Test cache clearing."""
        mock_normalizer = Mock()
        mock_normalizer.clear_cache = Mock()

        self.data_prep.clear_cache(mock_normalizer)

        mock_normalizer.clear_cache.assert_called_once()

    def test_clear_cache_no_clear_cache_method(self):
        """Test cache clearing when normalizer doesn't have clear_cache method."""
        mock_normalizer = Mock()
        del mock_normalizer.clear_cache

        # Should not raise error even if normalizer doesn't have clear_cache
        with pytest.raises(AttributeError):
            self.data_prep.clear_cache(mock_normalizer)

    def test_prepare_context_debug_data_structure(self):
        """Test that debug data has the correct structure."""
        mock_normalizer = Mock()
        mock_normalizer.normalize.return_value = ["test", "tokens"]

        mock_aliases = [
            ("product1", "Test Product", ["test", "product"]),
        ]
        self.data_prep._get_normalized_aliases = Mock(return_value=mock_aliases)

        self.data_prep.prepare_context(
            mock_normalizer, "test input", self.mock_backend, self.debug
        )

        # Get debug steps with data
        debug_steps = self.debug.get_debug_info()
        data_step = next((step for step in debug_steps if step.data is not None), None)

        assert data_step is not None
        assert "input_tokens" in data_step.data
        assert "normalized_aliases" in data_step.data
        assert data_step.data["input_tokens"] == ["test", "tokens"]

        # Verify normalized_aliases structure
        aliases_data = data_step.data["normalized_aliases"]
        assert len(aliases_data) == 1
        assert aliases_data[0]["product_id"] == "product1"
        assert aliases_data[0]["original_alias"] == "Test Product"
        assert aliases_data[0]["normalized_tokens"] == ["test", "product"]

    def test_prepare_context_indexes_barcodes(self):
        """Barcode digits survive number-stripping and match a zero-prefixed catalog code."""
        mock_normalizer = Mock()
        mock_normalizer.normalize.return_value = []
        self.data_prep._get_normalized_aliases = Mock(
            return_value=[("p1", "Gusanitos", ["gusanitos"])]
        )
        self.mock_backend.adapter.get_all_products.return_value = [
            ExternalProduct(id="p1", aliases=["Gusanitos"], barcode="08412345678903")
        ]

        context = self.data_prep.prepare_context(
            mock_normalizer, "8412345678903", self.mock_backend, self.debug
        )

        assert context.input_tokens == []
        assert context.barcodes["p1"] == context.query_barcodes[0]
        assert context.query_barcodes == ["8412345678903"]
