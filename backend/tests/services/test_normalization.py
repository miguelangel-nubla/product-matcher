"""
Simple tests for text normalization.
"""

from app.services.normalization import normalize_text


class TestNormalization:
    """Test basic normalization functionality."""

    def test_normalize_text_english(self):
        """Test basic English normalization."""
        result = normalize_text("Red Apple Juice", "en")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_normalize_text_spanish(self):
        """Test basic Spanish normalization."""
        result = normalize_text("Jugo de Manzana", "es")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_normalize_text_empty(self):
        """Test normalization with empty input."""
        result = normalize_text("", "en")
        assert result == []

    def test_normalize_text_whitespace(self):
        """Test normalization with only whitespace."""
        result = normalize_text("   ", "en")
        assert result == []

    def test_normalize_text_unknown_language(self):
        """Test normalization with unknown language falls back gracefully."""
        result = normalize_text("test product", "xx")
        assert isinstance(result, list)
