"""Semantic Preservation scorer.

This is a *deterministic proxy* for meaning preservation. It does NOT
claim to measure true semantic equivalence. It combines:

  * critical-constraint satisfaction (facts that must survive)
  * numeric/date/unit/entity preservation
  * best-reference lexical/character similarity (informational only)
  * response completeness (non-empty, sensible length)

Limitations are documented in docs/evaluation-methodology.md. When an
LLM judge is configured, its rubric-based score replaces this proxy and
is stored with provenance 'llm_judge'.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.schemas import BenchmarkExample
from app.evaluation.constraints import constraint_score, numeric_preservation_score
from app.evaluation.text_utils import best_reference_similarity, normalize_for_match


@dataclass
class SemanticResult:
    score: float | None
    available: bool = True
    components: dict[str, float] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    method: str = "deterministic_proxy"


# Component weights inside the semantic composite (configurable).
DEFAULT_COMPONENT_WEIGHTS = {
    "constraint_satisfaction": 0.45,
    "numeric_entity_preservation": 0.25,
    "reference_overlap": 0.20,
    "completeness": 0.10,
}


def completeness_score(example: BenchmarkExample, response: str) -> float:
    """Sensible-length check: non-empty and within a sane length band."""
    text = response.strip()
    if not text:
        return 0.0
    ref_lengths = [len(normalize_for_match(r)) for r in example.references] or [
        len(normalize_for_match(example.source_text))
    ]
    target = sum(ref_lengths) / len(ref_lengths)
    if target == 0:
        return 0.5
    ratio = len(normalize_for_match(text)) / target
    if ratio < 0.25:
        return 0.3  # far too short: likely omission
    if ratio < 0.6:
        return 0.6
    if ratio <= 2.5:
        return 1.0
    return 0.7  # verbose but not penalized heavily


def semantic_preservation_score(
    example: BenchmarkExample,
    response: str,
    component_weights: dict[str, float] | None = None,
) -> SemanticResult:
    """Compute the deterministic semantic-preservation proxy."""
    weights = component_weights or DEFAULT_COMPONENT_WEIGHTS

    # An empty response cannot preserve any meaning.
    if not response.strip():
        return SemanticResult(
            score=0.0,
            available=True,
            components={
                "constraint_satisfaction": 0.0,
                "numeric_entity_preservation": 0.0,
                "reference_overlap": 0.0,
                "completeness": 0.0,
            },
            evidence=["empty response"],
            method="deterministic_proxy",
        )

    c_score, checks = constraint_score(example, response)
    n_score, n_detail = numeric_preservation_score(example, response)
    overlap = best_reference_similarity(response, example.references)
    comp = completeness_score(example, response)

    components = {
        "constraint_satisfaction": round(c_score, 4),
        "numeric_entity_preservation": round(n_score, 4),
        "reference_overlap": round(overlap, 4),
        "completeness": round(comp, 4),
    }

    # Renormalize over the components that are actually present, tolerating a
    # partial custom weight map (a missing key must not raise KeyError).
    total_weight = sum(weights.get(k, 0.0) for k in components)
    if total_weight <= 0:
        score = None
        available = False
    else:
        score = sum(components[k] * weights.get(k, 0.0) for k in components) / total_weight
        available = True

    evidence: list[str] = []
    for chk in checks:
        if not chk.passed:
            evidence.append(f"constraint failed ({chk.kind}): {chk.detail}")
    if n_detail.get("missing"):
        evidence.append(f"missing from source: {', '.join(n_detail['missing'])}")
    if comp < 1.0:
        evidence.append(f"completeness sub-score {comp:.2f}")

    return SemanticResult(
        score=round(score, 4) if score is not None else None,
        available=available,
        components=components,
        evidence=evidence,
        method="deterministic_proxy",
    )
