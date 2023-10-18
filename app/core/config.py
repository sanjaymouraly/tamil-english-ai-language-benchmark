"""Application configuration backed by environment variables.

All settings are typed with Pydantic so the configuration surface is validated
and documented in one place. Secrets are read from the environment only and are
never persisted to disk or logs.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATA_DIR = Path("data")
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "teb.db"


def _env(*names: str) -> AliasChoices:
    """Accept both the ``TEB_``-prefixed and the bare environment variable name.

    Provider credentials conventionally live in bare variables such as
    ``OPENAI_API_KEY``, while this application namespaces its settings with
    ``TEB_``. Accepting both means a user can drop a standard key into the
    environment (or ``.env``) and have it picked up without renaming, which is
    what the "easy connect" provider setup relies on.
    """
    choices: list[str] = []
    for name in names:
        choices.extend([f"TEB_{name}", name])
    return AliasChoices(*choices)


class Settings(BaseSettings):
    """Runtime settings populated from the environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="TEB_",
        extra="ignore",
        case_sensitive=False,
    )

    env: str = "development"
    data_dir: Path = DEFAULT_DATA_DIR
    db_path: Path = DEFAULT_DB_PATH
    log_level: str = "INFO"

    # Spending / safety limits
    max_cost_usd: float = Field(default=1.00, ge=0.0)
    max_requests_per_job: int = Field(default=500, ge=1)
    request_timeout_seconds: float = Field(default=60.0, gt=0.0)
    max_concurrency: int = Field(default=4, ge=1, le=64)

    # Response cache (hash-keyed; safe to disable).
    cache_enabled: bool = True

    # Provider credentials (empty by default -> offline/mock mode).
    # Each field accepts both `TEB_<NAME>` and the bare `<NAME>` env var.
    openai_api_key: str = Field(default="", validation_alias=_env("OPENAI_API_KEY"))
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", validation_alias=_env("OPENAI_BASE_URL")
    )
    openai_model: str = Field(default="gpt-4o-mini", validation_alias=_env("OPENAI_MODEL"))

    anthropic_api_key: str = Field(default="", validation_alias=_env("ANTHROPIC_API_KEY"))
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com", validation_alias=_env("ANTHROPIC_BASE_URL")
    )
    anthropic_model: str = Field(
        default="claude-3-5-haiku-20241022", validation_alias=_env("ANTHROPIC_MODEL")
    )

    openrouter_api_key: str = Field(default="", validation_alias=_env("OPENROUTER_API_KEY"))
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", validation_alias=_env("OPENROUTER_BASE_URL")
    )
    openrouter_model: str = Field(default="", validation_alias=_env("OPENROUTER_MODEL"))

    custom_api_key: str = Field(default="", validation_alias=_env("CUSTOM_API_KEY"))
    custom_base_url: str = Field(default="", validation_alias=_env("CUSTOM_BASE_URL"))
    custom_model: str = Field(default="", validation_alias=_env("CUSTOM_MODEL"))

    ollama_base_url: str = Field(
        default="http://localhost:11434/v1", validation_alias=_env("OLLAMA_BASE_URL")
    )
    ollama_model: str = Field(default="llama3.1", validation_alias=_env("OLLAMA_MODEL"))

    lmstudio_base_url: str = Field(
        default="http://localhost:1234/v1", validation_alias=_env("LMSTUDIO_BASE_URL")
    )
    lmstudio_model: str = Field(default="local-model", validation_alias=_env("LMSTUDIO_MODEL"))

    @field_validator("log_level")
    @classmethod
    def _check_log_level(cls, v: str) -> str:
        return v.upper()

    @property
    def live_providers_configured(self) -> dict[str, bool]:
        return {
            "openai": bool(self.openai_api_key),
            "anthropic": bool(self.anthropic_api_key),
            "openrouter": bool(self.openrouter_api_key),
            "custom": bool(self.custom_api_key and self.custom_base_url),
            "ollama": True,  # local; availability checked at runtime
            "lmstudio": True,  # local; availability checked at runtime
        }

    def redacted_view(self) -> dict[str, Any]:
        """A view of settings safe for logs/UI: credentials are masked."""
        raw = self.model_dump()
        for key in list(raw):
            if "api_key" in key:
                raw[key] = "***" if raw[key] else ""
        return raw


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    """Test helper: clear the cached settings singleton."""
    get_settings.cache_clear()
