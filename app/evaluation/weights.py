"""Configurable score weights. Semantic and terminology scores are
ALWAYS reported separately, even when excluded from the composite."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

DEFAULT_WEIGHTS: dict[str, float] = {
    "semantic_preservation": 0.45,
    "terminology_consistency": 0.20,
    "entity_number_preservation": 0.10,
    "constraint_satisfaction": 0.15,
    "script_validity": 0.05,
    "completeness": 0.05,
}

DEFAULT_THRESHOLDS = {"pass": 0.7}


class ScoreWeights(BaseModel):
    weights: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    thresholds: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_THRESHOLDS))

    @model_validator(mode="after")
    def _validate(self) -> ScoreWeights:
        if not self.weights:
            raise ValueError("weights must not be empty")
        if any(w < 0 for w in self.weights.values()):
            raise ValueError("weights must be non-negative")
        return self

    def composite(self, dimension_scores: dict[str, float | None]) -> float | None:
        """Weighted mean over dimensions that produced a score.

        Weights are renormalized over the available dimensions so a
        missing (unsupported) dimension never silently skews the score.
        """
        total = 0.0
        weight_sum = 0.0
        for dim, score in dimension_scores.items():
            if score is None:
                continue
            w = self.weights.get(dim, 0.0)
            total += w * score
            weight_sum += w
        if weight_sum <= 0:
            return None
        return round(total / weight_sum, 4)
