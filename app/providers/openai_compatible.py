"""Generic OpenAI-compatible REST adapter.

Covers: OpenAI API, OpenRouter, Ollama, LM Studio, vLLM, and any
custom OpenAI-compatible endpoint. Uses httpx directly so no SDK
dependency is required.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.errors import ProviderError
from app.providers.base import GenerationRequest, GenerationResult, ProviderAdapter
from app.providers.cache import ResponseCache, request_cache_key
from app.providers.cost import estimate_cost_usd
from app.providers.retry import RetryPolicy, retry_call


class OpenAICompatibleAdapter(ProviderAdapter):
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str = "",
        model: str = "",
        timeout: float = 60.0,
        retry_policy: RetryPolicy | None = None,
        local: bool = False,
        cache: ResponseCache | None = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.retry_policy = retry_policy or RetryPolicy()
        # Local inference servers (Ollama, LM Studio, vLLM on localhost) are
        # free: report $0.00 rather than "unknown", which would otherwise make
        # local runs look like they had unmeasurable cost.
        self.local = local
        # Optional response cache (hash-keyed; prompts are never stored as keys).
        self.cache = cache

    # ------------------------------------------------------------------
    def generate(self, request: GenerationRequest) -> GenerationResult:
        import time

        model = request.model or self.model
        if not model:
            raise ProviderError(
                f"provider '{self.name}' has no model configured", provider=self.name
            )
        cache = self.cache
        cache_key = request_cache_key(self.name, model, request) if cache is not None else None
        if cache is not None and cache_key is not None:
            hit = cache.get(cache_key)
            if hit is not None:
                payload = dict(hit)
                payload["cached"] = True
                payload["latency_ms"] = 0
                return GenerationResult.model_validate(payload)

        started = time.monotonic()
        payload = self._build_payload(model, request)

        def _call() -> httpx.Response:
            headers = self._headers()
            return httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )

        response = retry_call(_call, policy=self.retry_policy)
        latency_ms = int((time.monotonic() - started) * 1000)
        result = self._parse(response, model, latency_ms)
        if cache is not None and cache_key is not None:
            cache.put(cache_key, result.model_dump(exclude={"raw"}))
        return result

    def test_connection(self) -> dict[str, Any]:
        try:
            response = httpx.get(
                f"{self.base_url}/models",
                headers=self._headers(),
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
        models: list[str] = []
        try:
            data = response.json()
            for item in data.get("data", [])[:50]:
                models.append(item.get("id", ""))
        except ValueError:
            pass
        return {"ok": True, "provider": self.name, "models": models}

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float | None:
        if self.local:
            return 0.0
        return estimate_cost_usd(self.model, prompt_tokens, completion_tokens)

    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_payload(self, model: str, request: GenerationRequest) -> dict[str, Any]:
        return {
            "model": model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

    def _parse(self, response: httpx.Response, model: str, latency_ms: int) -> GenerationResult:
        if response.status_code >= 400:
            detail = (
                response.text[:300].replace(self.api_key, "***")
                if self.api_key
                else response.text[:300]
            )
            raise ProviderError(
                f"{self.name} returned HTTP {response.status_code}: {detail}",
                provider=self.name,
                status_code=response.status_code,
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError(f"{self.name} returned invalid JSON", provider=self.name) from exc
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError(f"{self.name} returned no choices", provider=self.name)
        message = choices[0].get("message", {}) or {}
        text = message.get("content", "")
        if not isinstance(text, str):
            text = ""
        if not text.strip():
            # Some models (notably "reasoning" models such as qwen3) emit a
            # thinking trace in a separate `reasoning` field and can consume the
            # entire token budget before producing an answer, leaving `content`
            # empty. Surface this explicitly instead of silently recording an
            # empty (and therefore misleadingly low) evaluation.
            reasoning = message.get("reasoning") or message.get("reasoning_content") or ""
            if reasoning:
                raise ProviderError(
                    f"{self.name} returned an empty answer after a reasoning trace "
                    f"({len(reasoning)} chars). Raise max_tokens (e.g. --max-tokens 2048) "
                    "or use a non-reasoning model.",
                    provider=self.name,
                )
            raise ProviderError(
                f"{self.name} returned empty content for model '{model}'.",
                provider=self.name,
            )
        usage = data.get("usage") or {}
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        cost = 0.0 if self.local else estimate_cost_usd(model, prompt_tokens, completion_tokens)
        return GenerationResult(
            text=text,
            model_id=model,
            provider=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
            raw=data,
        )
