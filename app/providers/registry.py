"""Provider registry and factory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.core.errors import ProviderError
from app.providers.anthropic import AnthropicAdapter
from app.providers.base import ProviderAdapter
from app.providers.cache import ResponseCache
from app.providers.mock import MockProvider
from app.providers.offline import OfflineProvider
from app.providers.openai_compatible import OpenAICompatibleAdapter

PROVIDER_NAMES = (
    "mock",
    "offline",
    "openai",
    "anthropic",
    "openrouter",
    "ollama",
    "lmstudio",
    "custom",
)


class ProviderRegistry:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._offline_provider: OfflineProvider | None = None
        self._cache: ResponseCache | None = None
        if self.settings.cache_enabled:
            cache_file = Path(self.settings.data_dir) / "cache" / "responses.json"
            self._cache = ResponseCache(cache_file)

    def create(self, name: str, model: str | None = None) -> ProviderAdapter:
        s = self.settings
        timeout = s.request_timeout_seconds
        cache = self._cache
        if name == "mock":
            return MockProvider()
        if name == "offline":
            if self._offline_provider is None:
                raise ProviderError(
                    "offline provider requires a responses file; call set_offline_file() first",
                    provider=name,
                )
            if model:
                # Let the caller label the imported responses as a distinct model.
                self._offline_provider.model_label = model
                self._offline_provider.model = model
            return self._offline_provider
        if name == "openai":
            if not s.openai_api_key:
                raise ProviderError(
                    "OPENAI_API_KEY not set; OpenAI requires an API key (ChatGPT Plus is NOT enough)",
                    provider=name,
                )
            return OpenAICompatibleAdapter(
                name="openai",
                base_url=s.openai_base_url,
                api_key=s.openai_api_key,
                model=model or s.openai_model,
                timeout=timeout,
                cache=cache,
            )
        if name == "anthropic":
            if not s.anthropic_api_key:
                raise ProviderError("ANTHROPIC_API_KEY not set", provider=name)
            return AnthropicAdapter(
                api_key=s.anthropic_api_key,
                model=model or s.anthropic_model,
                base_url=s.anthropic_base_url,
                timeout=timeout,
                cache=cache,
            )
        if name == "openrouter":
            if not s.openrouter_api_key:
                raise ProviderError("OPENROUTER_API_KEY not set", provider=name)
            return OpenAICompatibleAdapter(
                name="openrouter",
                base_url=s.openrouter_base_url,
                api_key=s.openrouter_api_key,
                model=model or s.openrouter_model or "",
                timeout=timeout,
                cache=cache,
            )
        if name == "ollama":
            return OpenAICompatibleAdapter(
                name="ollama",
                base_url=s.ollama_base_url,
                model=model or s.ollama_model,
                timeout=timeout,
                local=True,
                cache=cache,
            )
        if name == "lmstudio":
            return OpenAICompatibleAdapter(
                name="lmstudio",
                base_url=s.lmstudio_base_url,
                model=model or s.lmstudio_model,
                timeout=timeout,
                local=True,
                cache=cache,
            )
        if name == "custom":
            if not s.custom_base_url:
                raise ProviderError("CUSTOM_BASE_URL not set for custom provider", provider=name)
            return OpenAICompatibleAdapter(
                name="custom",
                base_url=s.custom_base_url,
                api_key=s.custom_api_key,
                model=model or s.custom_model or "",
                timeout=timeout,
                cache=cache,
            )
        raise ProviderError(f"unknown provider: {name}", provider=name)

    def set_offline_file(self, path) -> OfflineProvider:
        self._offline_provider = OfflineProvider(path)
        return self._offline_provider

    def discover_models(self, name: str) -> list[str]:
        """List models a provider advertises (best-effort, never raises).

        Used by the "easy connect" UI so users can pick a real, installed model
        instead of guessing an identifier.
        """
        try:
            adapter = self.create(name)
        except Exception:
            return []
        status = adapter.test_connection()
        models = status.get("models") if isinstance(status, dict) else None
        return [m for m in models if m] if models else []

    def list_configured(self) -> dict[str, Any]:
        s = self.settings
        return {
            "mock": {"configured": True, "note": "deterministic mock; demo data only"},
            "offline": {"configured": True, "note": "requires imported responses JSONL"},
            "openai": {
                "configured": bool(s.openai_api_key),
                "model": s.openai_model,
                "base_url": s.openai_base_url,
            },
            "anthropic": {"configured": bool(s.anthropic_api_key), "model": s.anthropic_model},
            "openrouter": {
                "configured": bool(s.openrouter_api_key),
                "model": s.openrouter_model or "(unset)",
            },
            "ollama": {
                "configured": True,
                "model": s.ollama_model,
                "base_url": s.ollama_base_url,
                "local": True,
            },
            "lmstudio": {
                "configured": True,
                "model": s.lmstudio_model,
                "base_url": s.lmstudio_base_url,
                "local": True,
            },
            "custom": {"configured": bool(s.custom_base_url), "model": s.custom_model or "(unset)"},
        }


def get_registry() -> ProviderRegistry:
    return ProviderRegistry()
