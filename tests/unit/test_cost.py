"""Unit tests for cost estimation and spending limits."""

from app.core.errors import CostLimitExceededError
from app.providers.cost import estimate_cost_usd, job_cost_estimate


def test_known_model_cost():
    cost = estimate_cost_usd("gpt-4o-mini", 1_000_000, 1_000_000)
    assert cost is not None
    assert cost == pytest_approx(cost, 0.75)  # 0.15 + 0.60


def test_local_model_costs_zero():
    assert estimate_cost_usd("llama3.1", 1000, 100) == 0.0
    assert estimate_cost_usd("", 1000, 100) == 0.0


def test_unknown_model_returns_none():
    assert estimate_cost_usd("totally-unknown-model-xyz", 1000, 100) is None


def test_job_cost_estimate():
    est = job_cost_estimate("gpt-4o-mini", 100, avg_prompt_tokens=250, avg_completion_tokens=150)
    assert est is not None
    assert est > 0


def test_job_cost_estimate_unknown():
    assert job_cost_estimate("mystery-model", 100) is None


def test_cost_limit_exceeded_error():
    err = CostLimitExceededError("too much")
    assert "too much" in str(err)


def pytest_approx(value, expected):
    class _Approx:
        def __eq__(self, other):
            return abs(other - expected) < 0.01

    return _Approx()
