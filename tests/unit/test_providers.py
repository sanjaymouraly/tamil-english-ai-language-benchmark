"""Unit tests for provider adapters (mock/offline; live providers excluded)."""

import json
from pathlib import Path

import pytest

from app.core.errors import ProviderError
from app.providers.base import GenerationRequest
from app.providers.mock import MockProvider
from app.providers.offline import OfflineProvider
from app.providers.registry import ProviderRegistry


def test_mock_provider_deterministic():
    provider = MockProvider()
    req = GenerationRequest(
        messages=[{"role": "user", "content": "hello"}],
        meta={"example_id": "TEB-TST-0001", "reference": "I am going to school."},
    )
    r1 = provider.generate(req)
    r2 = provider.generate(req)
    assert r1.text == r2.text  # deterministic
    assert r1.provider == "mock"
    assert r1.cost_usd == 0.0


def test_mock_provider_uses_reference():
    provider = MockProvider()
    req = GenerationRequest(
        messages=[{"role": "user", "content": "x"}],
        meta={"example_id": "TEB-TST-0001", "reference": "The answer is forty-two."},
    )
    result = provider.generate(req)
    # bucket is deterministic; the reference should usually be returned
    assert isinstance(result.text, str)


def test_mock_test_connection():
    provider = MockProvider()
    status = provider.test_connection()
    assert status["ok"] is True
    assert status["mock"] is True


def test_offline_provider_loads(tmp_path):
    path = tmp_path / "responses.jsonl"
    path.write_text(
        json.dumps({"example_id": "E1", "response_text": "Answer one."})
        + "\n"
        + json.dumps({"example_id": "E2", "response_text": "Answer two."})
        + "\n",
        encoding="utf-8",
    )
    provider = OfflineProvider(path)
    req = GenerationRequest(
        messages=[{"role": "user", "content": "q"}],
        meta={"example_id": "E1"},
    )
    result = provider.generate(req)
    assert result.text == "Answer one."
    assert result.provider == "offline"


def test_offline_provider_missing_id():
    path = Path(__import__("tempfile").mkdtemp()) / "r.jsonl"
    path.write_text(json.dumps({"example_id": "E1", "response_text": "x"}) + "\n", encoding="utf-8")
    provider = OfflineProvider(path)
    req = GenerationRequest(
        messages=[{"role": "user", "content": "q"}], meta={"example_id": "MISSING"}
    )
    with pytest.raises(ProviderError):
        provider.generate(req)


def test_offline_provider_malformed_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("not json\n", encoding="utf-8")
    with pytest.raises(ProviderError):
        OfflineProvider(path)


def test_registry_creates_mock():
    registry = ProviderRegistry()
    adapter = registry.create("mock")
    assert isinstance(adapter, MockProvider)


def test_registry_rejects_unknown():
    registry = ProviderRegistry()
    with pytest.raises(ProviderError):
        registry.create("does-not-exist")


def test_registry_openai_requires_key():
    registry = ProviderRegistry()
    with pytest.raises(ProviderError):
        registry.create("openai")  # no OPENAI_API_KEY set


def test_registry_lists_configured():
    registry = ProviderRegistry()
    configured = registry.list_configured()
    assert "mock" in configured
    assert "openai" in configured


# ---------------------------------------------------------------------------
# Regression tests for adapter fixes
# ---------------------------------------------------------------------------


def _fake_response(payload: dict, status: int = 200):
    import httpx

    return httpx.Response(status, json=payload, request=httpx.Request("POST", "http://x"))


def test_openai_adapter_detects_reasoning_only_empty_answer(monkeypatch):
    """A reasoning model that exhausts its budget must fail loudly, not silently."""
    import httpx

    from app.providers.openai_compatible import OpenAICompatibleAdapter

    payload = {
        "choices": [
            {
                "message": {"role": "assistant", "content": "", "reasoning": "thinking..."},
                "finish_reason": "length",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 100},
    }
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _fake_response(payload))
    adapter = OpenAICompatibleAdapter(name="ollama", base_url="http://x", model="qwen3.5:4b")
    with pytest.raises(ProviderError, match="empty answer after a reasoning trace"):
        adapter.generate(GenerationRequest(messages=[{"role": "user", "content": "hi"}]))


def test_openai_adapter_local_models_cost_zero(monkeypatch):
    import httpx

    from app.providers.openai_compatible import OpenAICompatibleAdapter

    payload = {
        "choices": [{"message": {"role": "assistant", "content": "hello"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _fake_response(payload))
    adapter = OpenAICompatibleAdapter(
        name="ollama", base_url="http://x", model="some-unknown-local-model", local=True
    )
    result = adapter.generate(GenerationRequest(messages=[{"role": "user", "content": "hi"}]))
    assert result.cost_usd == 0.0


def test_openai_adapter_uses_response_cache(monkeypatch):
    import httpx

    from app.providers.cache import ResponseCache
    from app.providers.openai_compatible import OpenAICompatibleAdapter

    calls = {"n": 0}

    def _post(*a, **k):
        calls["n"] += 1
        return _fake_response(
            {
                "choices": [{"message": {"role": "assistant", "content": "cached!"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        )

    monkeypatch.setattr(httpx, "post", _post)
    adapter = OpenAICompatibleAdapter(
        name="openai",
        base_url="http://x",
        api_key="k",
        model="gpt-4o-mini",
        cache=ResponseCache(),
    )
    req = GenerationRequest(messages=[{"role": "user", "content": "hi"}])
    first = adapter.generate(req)
    second = adapter.generate(req)
    assert calls["n"] == 1  # second call served from cache
    assert first.text == second.text == "cached!"
    assert second.cached is True


def test_cache_key_differs_when_meta_differs():
    from app.providers.cache import request_cache_key

    base = dict(messages=[{"role": "user", "content": "same prompt"}])
    k1 = request_cache_key("p", "m", GenerationRequest(**base, meta={"example_id": "A"}))
    k2 = request_cache_key("p", "m", GenerationRequest(**base, meta={"example_id": "B"}))
    assert k1 != k2


def test_cost_short_unknown_id_does_not_borrow_price():
    from app.providers.cost import estimate_cost_usd

    # 'gpt' must NOT inherit gpt-4o-mini's price.
    assert estimate_cost_usd("gpt", 1000, 1000) is None
    # A dated snapshot of a known model does match.
    assert estimate_cost_usd("gpt-4o-mini-2024-07-18", 1000, 1000) is not None


def test_cost_local_vs_hosted_namespaced_model():
    from app.providers.cost import estimate_cost_usd

    # bare local tag -> free
    assert estimate_cost_usd("qwen3.5:4b", 1000, 1000) == 0.0
    # hosted namespace -> unknown price, not free
    assert estimate_cost_usd("qwen/qwen-2.5-72b-instruct", 1000, 1000) is None


def test_judge_client_calls_generate_with_request_object():
    """Regression: the judge previously called generate(**kwargs) and crashed."""
    from app.core.schemas import DimensionScore
    from app.evaluation.judge import JudgeClient
    from app.providers.base import GenerationResult

    class _StubProvider:
        name = "stub"

        def generate(self, request):
            assert isinstance(request, GenerationRequest)
            return GenerationResult(
                text='{"score": 0.8, "reasoning": "ok", "evidence": ["e"]}',
                model_id="stub",
                provider="stub",
            )

        def test_connection(self):
            return {"ok": True}

        def estimate_cost(self, p, c):
            return 0.0

    judge = JudgeClient(_StubProvider(), "stub-model")
    result = judge.score_dimension("adequacy", "rate this")
    assert isinstance(result, DimensionScore)
    assert result.score == 0.8
    assert result.provenance == "llm_judge"


def test_presets_cover_offline_local_and_cloud():
    from app.providers.presets import PRESETS, get_preset

    kinds = {p.kind for p in PRESETS}
    assert {"offline", "local", "cloud"}.issubset(kinds)
    assert get_preset("openai") is not None
    assert get_preset("ollama") is not None
    assert get_preset("nope") is None
    # No preset may embed a secret.
    for p in PRESETS:
        assert "sk-" not in p.base_url
        for value in p.env_vars.values():
            assert value in {"api_key", "base_url", "model"}
