"""Offline provider: replay previously imported model responses.

Responses are loaded from a JSONL file with records:
    {"example_id": "...", "response_text": "..."}

This enables full offline evaluation of pre-collected outputs
without calling any paid API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.errors import ProviderError
from app.providers.base import GenerationRequest, GenerationResult, ProviderAdapter


class OfflineProvider(ProviderAdapter):
    name = "offline"

    def __init__(self, responses_path: Path, model_label: str = "imported-responses") -> None:
        self.path = Path(responses_path)
        self.model_label = model_label
        # Expose `model` so the job records the label as its model id.
        self.model = model_label
        self._responses: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise ProviderError(f"offline response file not found: {self.path}", provider=self.name)
        with self.path.open(encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ProviderError(
                        f"invalid JSON on line {line_no}: {exc}", provider=self.name
                    ) from exc
                ex_id = rec.get("example_id") or rec.get("id")
                text = rec.get("response_text") or rec.get("response") or rec.get("text")
                if not ex_id or text is None:
                    raise ProviderError(
                        f"line {line_no} must contain 'example_id' and 'response_text'",
                        provider=self.name,
                    )
                self._responses[str(ex_id)] = str(text)

    @property
    def available_ids(self) -> set[str]:
        return set(self._responses)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        example_id = (request.meta or {}).get("example_id")
        if not example_id:
            raise ProviderError("offline provider requires meta.example_id", provider=self.name)
        if example_id in self._responses:
            return GenerationResult(
                text=self._responses[example_id],
                model_id=self.model_label,
                provider=self.name,
                latency_ms=0,
                cost_usd=0.0,
                raw={"source": "offline_import"},
            )
        raise ProviderError(f"no imported response for example {example_id}", provider=self.name)

    def test_connection(self) -> dict[str, Any]:
        return {"ok": True, "provider": self.name, "responses_loaded": len(self._responses)}

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float | None:
        return 0.0
