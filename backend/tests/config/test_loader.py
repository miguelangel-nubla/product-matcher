"""
Simple tests for config loader.
"""

from app.config.loader import get_global_settings


class TestConfigLoader:
    """Test basic config loading functionality."""

    def test_get_global_settings_default(self):
        """Test getting global settings with defaults."""
        settings = get_global_settings()
        assert isinstance(settings, dict)
        assert "default_threshold" in settings
        assert "max_candidates" in settings
        assert isinstance(settings["default_threshold"], float)
        assert isinstance(settings["max_candidates"], int)

    def test_get_global_settings_structure(self):
        """Test that global settings have the expected structure."""
        settings = get_global_settings()
        assert "default_threshold" in settings
        assert "max_candidates" in settings
        assert 0.0 <= settings["default_threshold"] <= 1.0
        assert settings["max_candidates"] > 0
