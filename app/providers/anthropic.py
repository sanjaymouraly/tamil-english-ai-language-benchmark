"""Anthropic Claude REST adapter."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.errors import ProviderError
from app.providers.base import GenerationRequest, GenerationResult, ProviderAdapter
from app.providers.cache import ResponseCache, request_cache_key
from app.providers.cost import estimate_cost_usd
from app.providers.retry import RetryPolicy, retry_call


class AnthropicAdapter(ProviderAdapter):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.anthropic.com",
        timeout: float = 60.0,
        retry_policy: RetryPolicy | None = None,
        cache: ResponseCache | None = None,
    ) -> None:
        self.name = "anthropic"
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_policy = retry_policy or RetryPolicy()
        self.cache = cache

    def generate(self, request: GenerationRequest) -> GenerationResult:
        model = request.model or self.model
        if not model:
            raise ProviderError("anthropic provider has no model configured", provider=self.name)
        cache = self.cache
        cache_key = request_cache_key(self.name, model, request) if cache is not None else None
        if cache is not None and cache_key is not None:
            hit = cache.get(cache_key)
            if hit is not None:
                cached_payload = dict(hit)
                cached_payload["cached"] = True
                cached_payload["latency_ms"] = 0
                return GenerationResult.model_validate(cached_payload)
        system = "\n".join(m["content"] for m in request.messages if m["role"] == "system")
        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in request.messages
            if m["role"] != "system"
        ]
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
        }
        if system:
            payload["system"] = system

        started = time.monotonic()

        def _call() -> httpx.Response:
            return httpx.post(
                f"{self.base_url}/v1/messages",
                json=payload,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )

        response = retry_call(_call, policy=self.retry_policy)
        latency_ms = int((time.monotonic() - started) * 1000)

        if response.status_code >= 400:
            detail = response.text[:300]
            if self.api_key:
                detail = detail.replace(self.api_key, "***")
            raise ProviderError(
                f"anthropic returned HTTP {response.status_code}: {detail}",
                provider=self.name,
                status_code=response.status_code,
            )
        data = response.json()
        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        usage = data.get("usage") or {}
        cost = estimate_cost_usd(model, usage.get("input_tokens"), usage.get("output_tokens"))
        result = GenerationResult(
            text=text,
            model_id=model,
            provider=self.name,
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            latency_ms=latency_ms,
            cost_usd=cost,
            raw=data,
        )
        if cache is not None and cache_key is not None:
            cache.put(cache_key, result.model_dump(exclude={"raw"}))
        return result

    def test_connection(self) -> dict[str, Any]:
        try:
            response = httpx.get(
                f"{self.base_url}/v1/models",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                timeout=self.timeout,
            )
        except Exception as exc:
            return {"ok": False, "provider": self.name, "error": f"{type(exc).__name__}: {exc}"}
        if response.status_code == 401:
            return {
                "ok": False,
                "provider": self.name,
                "error": "authentication failed (401) — check the API key",
            }
        if response.status_code >= 400:
            return {"ok": False, "provider": self.name, "error": f"HTTP {response.status_code}"}
        models = [m.get("id", "") for m in response.json().get("data", [])[:50]]
        return {"ok": True, "provider": self.name, "models": models}

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float | None:
        return estimate_cost_usd(self.model, prompt_tokens, completion_tokens)
