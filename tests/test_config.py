"""Tests for Pydantic Settings configuration."""

from core.config.settings import Settings


def test_settings_default_values():
    settings = Settings()
    assert settings.app_name == "AgentOS"
    assert settings.llm.default_provider == "gemini"
