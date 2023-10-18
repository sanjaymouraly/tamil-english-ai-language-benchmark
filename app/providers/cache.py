"""Response cache with safe (hash-only) keys.

Cache keys are SHA-256 hashes of the canonical request, so prompts
and credentials are never stored as keys. Responses are cached in
memory; an optional JSON file cache persists across runs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.providers.base import GenerationRequest


def request_cache_key(provider: str, model: str, request: GenerationRequest) -> str:
    """SHA-256 cache key over the full request (never stores prompts as keys).

    ``meta`` is included so that two requests which are identical in messages
    and decoding settings but differ in harness context cannot collide.
    """
    canonical = {
        "provider": provider,
        "model": model,
        "messages": request.messages,
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "meta": request.meta,
    }
    blob = json.dumps(canonical, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


class ResponseCache:
    def __init__(self, path: Path | None = None) -> None:
        self._memory: dict[str, dict[str, Any]] = {}
        self.path = path
        if path is not None and path.exists():
            try:
                self._memory = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._memory = {}

    def get(self, key: str) -> dict[str, Any] | None:
        return self._memory.get(key)

    def put(self, key: str, result: dict[str, Any]) -> None:
        self._memory[key] = result
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self._memory, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass  # cache is best-effort

    def clear(self) -> None:
        self._memory.clear()
        if self.path is not None and self.path.exists():
            self.path.unlink()
