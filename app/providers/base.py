"""Provider adapter interface shared by all backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    messages: list[dict[str, str]] = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1)
    model: str | None = None
    # Harness-only metadata (example id, references). Sent to mock/offline
    # providers only; live providers ignore it so references never leak
    # into a real prompt.
    meta: dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    text: str
    model_id: str
    provider: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: int = 0
    cost_usd: float | None = None
    cached: bool = False
    error: str | None = None
    raw: dict[str, Any] | None = None


class ProviderAdapter(ABC):
    """Common interface for every model provider."""

    name: str = "base"

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Generate one completion."""

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        """Return a connectivity/status payload; never raise raw secrets."""

    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float | None:
        """Estimated USD cost, or None when pricing is unknown."""
