"""Unit tests for configuration / environment handling."""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings, reset_settings_cache


@pytest.fixture(autouse=True)
def _reset():
    reset_settings_cache()
    yield
    reset_settings_cache()


def test_defaults_are_offline_safe():
    s = Settings(_env_file=None)
    assert s.openai_api_key == ""
    assert s.anthropic_api_key == ""
    assert s.openai_base_url == "https://api.openai.com/v1"
    assert s.max_cost_usd == 1.0


def test_bare_env_var_is_accepted(monkeypatch):
    """A standard `OPENAI_API_KEY` must be picked up without the TEB_ prefix."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-bare")
    monkeypatch.delenv("TEB_OPENAI_API_KEY", raising=False)
    assert Settings(_env_file=None).openai_api_key == "sk-bare"


def test_prefixed_env_var_is_accepted(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("TEB_ANTHROPIC_API_KEY", "sk-prefixed")
    assert Settings(_env_file=None).anthropic_api_key == "sk-prefixed"


def test_prefixed_takes_precedence_over_bare(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "bare")
    monkeypatch.setenv("TEB_OPENROUTER_API_KEY", "prefixed")
    assert Settings(_env_file=None).openrouter_api_key == "prefixed"


def test_redacted_view_masks_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
    view = Settings(_env_file=None).redacted_view()
    assert view["openai_api_key"] == "***"
    assert "sk-secret-value" not in str(view)


def test_log_level_is_upper_cased(monkeypatch):
    monkeypatch.setenv("TEB_LOG_LEVEL", "debug")
    assert Settings(_env_file=None).log_level == "DEBUG"


def test_get_settings_is_cached():
    assert get_settings() is get_settings()
