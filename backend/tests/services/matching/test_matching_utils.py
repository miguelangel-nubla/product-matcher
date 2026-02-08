"""Test cases for matching utilities."""

import pytest
from unittest.mock import Mock, patch

from app.services.matching.utils.es import SpanishMatchingUtils
from app.services.matching.utils.registry import MatchingUtilsRegistry, get_matching_utils, registry

class TestSpanishMatchingUtils:
    """Test cases for SpanishMatchingUtils."""

    def setup_method(self):
        """Set up test fixtures."""
        self.utils = SpanishMatchingUtils()
        
    def test_init(self):
        """Test initialization."""
        utils = SpanishMatchingUtils(config={"key": "value"})
        assert utils.config == {"key": "value"}
        assert utils._semantic_cache == {}

    def test_calculate_semantic_similarity_empty(self):
        """Test similarity with empty inputs."""
        assert self.utils.calculate_semantic_similarity([], []) == 0.0
        assert self.utils.calculate_semantic_similarity(["apple"], []) == 0.0
        assert self.utils.calculate_semantic_similarity([], ["apple"]) == 0.0

    @patch("app.services.normalization.es._nlp_model")
    def test_calculate_semantic_similarity_uncached(self, mock_nlp):
        """Test similarity calculation without cache."""
        # Mock Spacy docs and similarity
        mock_doc1 = Mock()
        mock_doc2 = Mock()
        # The mock is called with text1 and text2
        mock_nlp.side_effect = [mock_doc1, mock_doc2]
        mock_doc1.similarity.return_value = 0.85

        result = self.utils.calculate_semantic_similarity(["apple"], ["manzana"])
        
        assert result == 0.85
        # The text is joined tokens
        mock_nlp.assert_any_call("apple")
        mock_nlp.assert_any_call("manzana")
        mock_doc1.similarity.assert_called_once_with(mock_doc2)

    @patch("app.services.normalization.es._nlp_model")
    def test_calculate_semantic_similarity_cached(self, mock_nlp):
        """Test that results are cached."""
        # Setup mocks
        mock_doc1 = Mock()
        mock_doc2 = Mock()
        # First call: one doc for each input string
        mock_nlp.side_effect = [0.75, mock_doc1, mock_doc2]  # Wait, side_effect for a function called twice
        # But wait, logic is:
        # doc1 =nlp(text1)
        # doc2 =nlp(text2)
        # So it is called twice.
        
        # Let's verify caching logic more simply by pre-populating the cache
        # or just ensuring side_effect is only consumed once (pair of calls)
        
        mock_nlp.side_effect = [mock_doc1, mock_doc2]
        mock_doc1.similarity.return_value = 0.75

        # First call - should calculate
        # This consumes the 2 side_effect items
        result1 = self.utils.calculate_semantic_similarity(["a"], ["b"])
        assert result1 == 0.75
        assert len(self.utils._semantic_cache) == 1
        
        # Second call - should use cache and NOT call nlp
        result2 = self.utils.calculate_semantic_similarity(["a"], ["b"])
        assert result2 == 0.75
        
        # Verify call count: only 2 calls (for the first calculation)
        assert mock_nlp.call_count == 2

    def test_cache_key_generation(self):
        """Test that cache keys are consistent regardless of token order."""
        # Manually inject into cache to verify key structure
        tokens1 = ["b", "a"]
        tokens2 = ["d", "c"]
        key1 = "|".join(sorted(tokens1)) # "a|b"
        key2 = "|".join(sorted(tokens2)) # "c|d"
        expected_key = f"{key1}#{key2}"
        
        self.utils._semantic_cache[expected_key] = 0.99
        
        # Call with different order
        result = self.utils.calculate_semantic_similarity(["a", "b"], ["d", "c"])
        assert result == 0.99

    def test_clear_cache(self):
        """Test clearing the cache."""
        self.utils._semantic_cache["key"] = 1.0
        self.utils.clear_cache()
        assert len(self.utils._semantic_cache) == 0

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        self.utils._semantic_cache["key1"] = 1.0
        self.utils._semantic_cache["key2"] = 0.5
        
        stats = self.utils.get_cache_stats()
        assert stats["semantic_cache_size"] == 2
        assert stats["total_entries"] == 2


class TestMatchingUtilsRegistry:
    """Test matching utils registry."""

    def setup_method(self):
        self.registry = MatchingUtilsRegistry()

    def test_register_and_get(self):
        """Test registering and retrieving utils."""
        mock_utils = Mock()
        self.registry.register("en", mock_utils)
        assert self.registry.get("en") == mock_utils

    def test_get_unknown_language(self):
        """Test getting unknown language raises error."""
        with pytest.raises(ValueError):
            self.registry.get("xx")

    def test_list_languages(self):
        """Test listing registered languages."""
        self.registry.register("en", Mock())
        self.registry.register("es", Mock())
        langs = self.registry.list_languages()
        assert "en" in langs
        assert "es" in langs
