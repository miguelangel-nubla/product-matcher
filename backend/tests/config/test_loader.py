"""
Simple tests for config loader.
"""

from app.config.loader import get_global_settings


class TestConfigLoader:
    """Test basic config loading functionality."""

    def test_get_global_settings_default(self):
        """Test getting global settings with defaults."""
        from app.models import GlobalSettings
        settings = get_global_settings()
        assert isinstance(settings, GlobalSettings)
        assert hasattr(settings, "default_threshold")
        assert hasattr(settings, "max_candidates")
        assert isinstance(settings.default_threshold, float)
        assert isinstance(settings.max_candidates, int)

    def test_get_global_settings_structure(self):
        """Test that global settings have the expected structure."""
        settings = get_global_settings()
        assert hasattr(settings, "default_threshold")
        assert hasattr(settings, "max_candidates")
        assert 0.0 <= settings.default_threshold <= 1.0
        assert settings.max_candidates > 0
