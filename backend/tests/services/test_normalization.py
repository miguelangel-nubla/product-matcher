"""
Tests for text normalization.
"""

import pytest
from unittest.mock import Mock, patch

from app.services.normalization.registry import get_normalizer, registry
from app.services.normalization.es import SpanishNormalizer, post_process_tokens


class TestNormalization:
    """Test normalization functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Register Spanish normalizer for testing
        self.normalizer = SpanishNormalizer(config={})
        registry.register("es", self.normalizer)

    def test_normalize_text_english(self):
        """Test basic English normalization - skip for now as only Spanish is implemented."""
        pass

    def test_normalize_text_spanish_basic(self):
        """Test basic Spanish normalization."""
        try:
            result = self.normalizer.normalize("Jugo de Manzana")
            assert isinstance(result, list)
            # "de" is stopword, "Jugo" -> "jugo" (lemma), "Manzana" -> "manzana"
            assert "jugo" in result
            assert "manzana" in result
            assert "de" not in result
        except RuntimeError:
            pytest.skip("SpaCy model not available")

    def test_normalize_text_empty(self):
        """Test normalization with empty input."""
        result = self.normalizer.normalize("")
        assert result == []

    def test_normalize_text_whitespace(self):
        """Test normalization with only whitespace."""
        result = self.normalizer.normalize("   ")
        assert result == []

    def test_normalize_text_unknown_language(self):
        """Test normalization with unknown language."""
        try:
            get_normalizer("xx")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "No normalizer registered" in str(e)

    def test_normalize_stopwords_with_accents(self):
        """Test normalization removes stopwords even if input has accents."""
        try:
            # "rápido" -> "rapido" (stopword), "fácil" -> "facil" (stopword)
            result = self.normalizer.normalize("coches rápido fácil automático")
            assert "rapido" not in result
            assert "facil" not in result
            assert "automatico" not in result
            # "coches" -> "coche" (lemma) or keep "coches" if lemma fails locally
            assert "coche" in result or "coches" in result
        except RuntimeError:
             pytest.skip("SpaCy model not available")

    def test_post_process_roman_numerals(self):
        """Test removal of roman numerals."""
        tokens = ["carlos", "iii", "juan", "iv", "siglo", "xx"]
        processed = post_process_tokens(tokens)
        assert "iii" not in processed
        assert "iv" not in processed
        # "xx" might be considered roman numeral for 20? Yes.
        assert "xx" not in processed
        assert "carlos" in processed
        assert "juan" in processed

    def test_post_process_split_numbers(self):
        """Test splitting and removal of numbers."""
        # "750ml" -> "750", "ml" -> "ml" -> "mililitro" -> REMOVED (stopword)
        # We test with a non-stopword suffix to verify splitting logic
        tokens = ["botella", "750xyz", "2abc"]
        processed = post_process_tokens(tokens, stopwords=set(), expansions={})
        # 750 removed, 2 removed
        # xyz kept, abc kept
        assert "750" not in processed
        assert "2" not in processed
        assert "xyz" in processed
        assert "abc" in processed
        assert "botella" in processed

    def test_post_process_abbreviations(self):
        """Test abbreviation expansion."""
        # Use custom expansions where result is NOT a stopword
        expansions = {"tst": "testtoken"}
        tokens = ["tst", "other"]
        processed = post_process_tokens(tokens, expansions=expansions, stopwords=set())
        assert "testtoken" in processed
        assert "other" in processed

    def test_normalize_with_custom_config(self):
        """Test normalization with custom configuration."""
        custom_config = {
            "stopwords": ["manzana"], # treat manzana as stopword
            "expansions": {"jug": "jugo"}
        }
        # Create a new normalizer with custom config
        norm = SpanishNormalizer(config=custom_config)
        
        # Test custom stopword via public API if possible, but easier to unit test post_process
        tokens = ["manzana", "jug"]
        
        # Note: SpanishNormalizer.normalize() calls post_process with its instance config.
        # But here we want to test that the instance config was correctly loaded.
        assert "manzana" in norm.custom_stopwords
        assert norm.custom_expansions["jug"] == "jugo"

        # Apply using the loaded config
        processed = post_process_tokens(tokens, stopwords=norm.custom_stopwords, expansions=norm.custom_expansions)
        assert "manzana" not in processed
        assert "jugo" in processed

