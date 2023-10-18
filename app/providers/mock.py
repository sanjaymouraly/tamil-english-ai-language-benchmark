"""Deterministic mock provider for offline demos and tests.

Responses are derived from a hash of the example content, with
controlled, realistic flaws (dropped numbers, glossary misses,
script errors) so that demo runs show meaningful score variation.

MOCK OUTPUTS ARE NOT REAL MODEL PERFORMANCE. Any dashboard or
report built from them must be labeled 'demo data'.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.providers.base import GenerationRequest, GenerationResult, ProviderAdapter

MODEL_ID = "teb-mock-v1"

# Flaw probabilities (deterministic per example, derived from hash).
FLAW_BANDS = [
    (0.45, "good"),  # uses the first reference nearly verbatim
    (0.65, "flaw_minor"),  # drops a glossary variant or trims punctuation
    (0.80, "flaw_number"),  # perturbs one number
    (0.90, "flaw_term"),  # swaps a glossary term for an unapproved variant
    (1.00, "flaw_script"),  # responds in the wrong script
]


class MockProvider(ProviderAdapter):
    name = "mock"

    def __init__(self, model: str = MODEL_ID) -> None:
        self.model = model

    def generate(self, request: GenerationRequest) -> GenerationResult:
        user_text = ""
        for msg in request.messages:
            if msg.get("role") == "user":
                user_text = msg.get("content", "")
                break
        reference = None
        if request.meta and "reference" in request.meta:
            reference = request.meta.get("reference")
        else:
            reference = self._extract_reference(user_text)
        bucket = self._bucket(user_text or request.meta.get("example_id", ""))
        text = self._response_for(user_text, bucket, reference)
        return GenerationResult(
            text=text,
            model_id=self.model,
            provider=self.name,
            prompt_tokens=max(1, len(user_text) // 4),
            completion_tokens=max(1, len(text) // 4),
            latency_ms=0,
            cost_usd=0.0,
            raw={"mock": True, "bucket": bucket},
        )

    def test_connection(self) -> dict[str, Any]:
        return {"ok": True, "provider": self.name, "models": [MODEL_ID], "mock": True}

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float | None:
        return 0.0

    # ------------------------------------------------------------------
    def _bucket(self, text: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        value = int(digest[:8], 16) / 0xFFFFFFFF
        for threshold, label in FLAW_BANDS:
            if value <= threshold:
                return label
        return "good"

    def _response_for(self, text: str, bucket: str, reference: str | None = None) -> str:
        # Use the harness-provided reference when available (mock/offline
        # path only); otherwise fall back to a generic acknowledgement.
        if bucket == "good" and reference:
            return reference
        if bucket == "flaw_minor" and reference:
            return reference.rstrip(".?!") + " ."
        if bucket == "flaw_number" and reference:
            return self._perturb_number(reference)
        if bucket == "flaw_term" and reference:
            return self._swap_term(reference)
        if bucket == "flaw_script":
            return "The model responded in an unrelated language. Response text here."
        return reference or "I am unable to answer this question."

    @staticmethod
    def _extract_reference(prompt: str) -> str | None:
        # The evaluation harness passes the reference list inside the
        # judge-style prompt; for the benchmark runner we pass a
        # dedicated field. See BenchmarkRunner for the actual mapping.
        match = re.search(r"\[\[REF:(.*?)\]\]", prompt, flags=re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _perturb_number(text: str) -> str:
        def _bump(m: re.Match) -> str:
            num = m.group(0)
            digits = num.replace(",", "")
            try:
                value = int(digits)
            except ValueError:
                try:
                    value = int(float(digits))
                except ValueError:
                    return num
            return str(value + 1) if value < 10**9 else num

        return re.sub(r"\d[\d,]*", _bump, text, count=1)

    @staticmethod
    def _swap_term(text: str) -> str:
        swaps = {
            "database": "data store",
            "backup": "save copy",
            "server": "machine",
            "password": "passcode",
            "login": "sign-in",
            "தரவுத்தளம்": "தரவு அட்டவணை",
            "காப்பகப்படுத்தல்": "காப்பு செய்தல்",
            "சேவையகம்": "சேவை நிலையம்",
            "கடவுச்சொல்": "கடவு சொல்",
            "உள்நுழைவு": "நுழைவு",
        }
        for wrong, right in swaps.items():
            if wrong.lower() in text.lower():
                pattern = re.compile(re.escape(wrong), re.IGNORECASE)
                return pattern.sub(right, text, count=1)
        return text + " [terminology altered]"
