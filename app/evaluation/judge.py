"""Optional LLM-as-a-judge layer.

The judge is used ONLY when a provider is explicitly configured.
Its outputs are stored with provenance='llm_judge' and are never
treated as verified ground truth. Rubric prompts are versioned.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from app.core.schemas import DimensionScore
from app.evaluation.rubrics import JUDGE_PROMPT_VERSION

if TYPE_CHECKING:
    from app.providers.base import ProviderAdapter


def parse_judge_json(text: str) -> dict | None:
    """Extract the first JSON object from judge output."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


class JudgeClient:
    """Rubric-based judge built on any provider adapter."""

    def __init__(
        self, provider: ProviderAdapter, model_id: str, rubric_version: str = JUDGE_PROMPT_VERSION
    ) -> None:
        self.provider = provider
        self.model_id = model_id
        self.rubric_version = rubric_version
        self.judgments: list[dict] = []

    def score_dimension(self, dimension: str, prompt: str) -> DimensionScore | None:
        from app.providers.base import GenerationRequest

        try:
            gen = self.provider.generate(
                GenerationRequest(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=512,
                    model=self.model_id or None,
                )
            )
        except Exception as exc:  # judge failure must not crash the job
            return DimensionScore(
                dimension=dimension,
                score=None,
                available=False,
                provenance="llm_judge",
                evidence=[f"judge call failed: {type(exc).__name__}"],
            )
        parsed = parse_judge_json(gen.text)
        if parsed is None or "score" not in parsed:
            return DimensionScore(
                dimension=dimension,
                score=None,
                available=False,
                provenance="llm_judge",
                evidence=["judge output was not valid JSON"],
            )
        try:
            raw = float(parsed["score"])
        except (TypeError, ValueError):
            return DimensionScore(
                dimension=dimension,
                score=None,
                available=False,
                provenance="llm_judge",
                evidence=["judge score was not numeric"],
            )
        score = min(1.0, max(0.0, raw))  # clamp 0..1
        reasoning = str(parsed.get("reasoning", ""))
        evidence = list(parsed.get("evidence", []))
        if isinstance(evidence, str):
            evidence = [evidence]
        return DimensionScore(
            dimension=dimension,
            score=round(score, 4),
            available=True,
            provenance="llm_judge",
            evidence=[f"judge_model={self.model_id}", f"reasoning: {reasoning}", *evidence],
            rubric_version=self.rubric_version,
            confidence=None,
        )
