"""Evaluation engine: orchestrates layered scoring for one example.

Layers:
  1. Deterministic checks (constraints, glossary, entities, script)
  2. Reference-based similarity (informational)
  3. Optional LLM-as-judge (rubric-based, marked as judge output)
  4. Human review (recorded separately in the annotation module)

The engine never equates lexical overlap with semantic correctness:
overlap feeds only a small component of the semantic proxy, and the
proxy itself is clearly labeled.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.core.schemas import BenchmarkExample, DimensionScore, EvaluationRecord
from app.evaluation import metrics, terminology
from app.evaluation.constraints import numeric_preservation_score
from app.evaluation.rubrics import RUBRIC_VERSION, rubric_prompt
from app.evaluation.semantic import SemanticResult, semantic_preservation_score
from app.evaluation.weights import ScoreWeights

if TYPE_CHECKING:
    pass

# Dimensions requiring a judge or human (unavailable by default).
JUDGE_DIMENSIONS = [
    "adequacy",
    "naturalness",
    "cultural_suitability",
    "code_mix_appropriateness",
    "hallucination",
]

ErrorTaxonomy = {
    "empty_response": "Response is empty",
    "omission": "Required fact or constraint missing",
    "numeric_error": "Number/date/unit altered or dropped",
    "terminology_miss": "Glossary term not translated as specified",
    "terminology_inconsistent": "Same concept translated with multiple variants",
    "script_error": "Wrong script for target language",
    "negation_error": "Negation or prohibition violated",
    "structural_error": "Required output structure not followed",
    "hallucination": "Unsupported content added (numbers not in source)",
    "transliteration_error": "Romanization or Tamil-script rendering wrong",
}


@dataclass
class EngineOutput:
    record: EvaluationRecord
    errors: list[str] = field(default_factory=list)


class EvaluationEngine:
    """Layer-aware evaluation engine."""

    def __init__(
        self,
        weights: ScoreWeights | None = None,
        judge_callback: Callable[[str, str], DimensionScore | None] | None = None,
    ) -> None:
        self.weights = weights or ScoreWeights()
        self.judge_callback = judge_callback

    # ------------------------------------------------------------------
    def evaluate(
        self,
        example: BenchmarkExample,
        response: str,
        model_id: str = "",
        job_id: str | None = None,
    ) -> EngineOutput:
        started = time.monotonic()
        errors: list[str] = []

        if not response.strip():
            errors.append(ErrorTaxonomy["empty_response"])

        dimensions: dict[str, DimensionScore] = {}

        # ---- Layer 1: deterministic -----------------------------------
        c_score, checks = _constraint_score(example, response)
        dimensions["constraint_satisfaction"] = DimensionScore(
            dimension="constraint_satisfaction",
            score=c_score,
            provenance="deterministic",
            evidence=[f"{c.kind}: {'PASS' if c.passed else 'FAIL'} ({c.detail})" for c in checks],
        )
        for chk in checks:
            if not chk.passed:
                if chk.kind in {"must_not_contain"}:
                    errors.append(f"negation_error: {ErrorTaxonomy['negation_error']}")
                else:
                    errors.append(f"omission: {ErrorTaxonomy['omission']}")

        n_score, n_detail = numeric_preservation_score(example, response)
        dimensions["entity_number_preservation"] = DimensionScore(
            dimension="entity_number_preservation",
            score=n_score,
            provenance="deterministic",
            evidence=[f"source entities: {n_detail.get('source_entities', [])}"]
            + ([f"missing: {', '.join(n_detail['missing'])}"] if n_detail.get("missing") else []),
        )
        if n_detail.get("missing"):
            errors.append(f"numeric_error: {ErrorTaxonomy['numeric_error']}")

        sem: SemanticResult = semantic_preservation_score(example, response)
        dimensions["semantic_preservation"] = DimensionScore(
            dimension="semantic_preservation",
            score=sem.score,
            available=sem.available,
            provenance="deterministic",
            evidence=sem.evidence + [f"components={sem.components}"],
            notes="Deterministic proxy; replace with judge/human for production claims.",
        )

        term = terminology.glossary_adherence(example, response)
        dimensions["terminology_consistency"] = DimensionScore(
            dimension="terminology_consistency",
            score=term.score,
            available=term.available,
            provenance="deterministic",
            evidence=term.evidence + [f"applicable terms: {term.applicable_terms}"],
        )
        for detail in term.term_details:
            if not detail.hit:
                errors.append(f"terminology_miss: {ErrorTaxonomy['terminology_miss']}")

        script = metrics.script_validity_score(example, response)
        dimensions["script_validity"] = DimensionScore(
            dimension="script_validity",
            score=script.score,
            provenance="deterministic",
            evidence=script.evidence
            + [f"expected={script.expected_script} detected={script.detected_script}"],
        )
        if script.score == 0.0:
            errors.append(f"script_error: {ErrorTaxonomy['script_error']}")

        comp = _completeness(example, response)
        dimensions["completeness"] = DimensionScore(
            dimension="completeness", score=comp, provenance="deterministic"
        )

        flu, flu_evidence = metrics.fluency_heuristics(response)
        dimensions["fluency"] = DimensionScore(
            dimension="fluency",
            score=flu,
            provenance="deterministic",
            evidence=flu_evidence,
            notes="heuristic only — not a fluency judgment",
        )

        # ---- Transliteration for romanized tasks --------------------
        if example.category.value == "romanized_transliteration":
            t_score, t_detail = metrics.transliteration_score(example, response)
            dimensions["transliteration_accuracy"] = DimensionScore(
                dimension="transliteration_accuracy",
                score=t_score,
                provenance="deterministic",
                evidence=[str(t_detail)],
            )
            if t_score < 0.5:
                errors.append(f"transliteration_error: {ErrorTaxonomy['transliteration_error']}")

        # ---- Instruction-following (structural) ---------------------
        # Scored only from requirements we can check deterministically
        # (regex constraints plus an explicit list-format instruction).
        # When the example defines no such requirement the dimension is
        # marked unavailable rather than being given an invented score.
        if example.category.value == "instruction_following":
            structural_checks: list[tuple[str, bool]] = []
            for constraint in example.critical_constraints:
                if constraint.kind.value != "regex":
                    continue
                matched = False
                for pattern in constraint.alternatives:
                    try:
                        if re.search(pattern, response, re.UNICODE | re.MULTILINE):
                            matched = True
                            break
                    except re.error:
                        matched = False
                structural_checks.append((f"regex:{constraint.alternatives[0]}", matched))
            if _requires_list(example):
                structural_checks.append(
                    ("list_structure", metrics.structure_check(response, "list") > 0.0)
                )

            if structural_checks:
                if_score = sum(1 for _, ok in structural_checks if ok) / len(structural_checks)
                dimensions["instruction_following"] = DimensionScore(
                    dimension="instruction_following",
                    score=round(if_score, 4),
                    provenance="deterministic",
                    evidence=[
                        f"{name}: {'PASS' if ok else 'FAIL'}" for name, ok in structural_checks
                    ],
                )
                if if_score < 1.0:
                    errors.append(f"structural_error: {ErrorTaxonomy['structural_error']}")
            else:
                dimensions["instruction_following"] = DimensionScore(
                    dimension="instruction_following",
                    score=None,
                    available=False,
                    provenance="deterministic",
                    evidence=["no deterministic structural requirement defined"],
                    notes="Instruction-following is unavailable without a checkable requirement.",
                )

        # ---- Layer 3: optional LLM judge -----------------------------
        if self.judge_callback is not None:
            for dim in JUDGE_DIMENSIONS:
                scored = self.judge_callback(
                    dim, rubric_prompt(dim, example.source_text, example.references, response)
                )
                if scored is not None:
                    dimensions[dim] = scored

        # ---- Composite ------------------------------------------------
        dimension_scores = {k: (v.score if v.available else None) for k, v in dimensions.items()}
        overall = self.weights.composite(dimension_scores)
        semantic_val = dimensions["semantic_preservation"].score
        term_val = dimensions["terminology_consistency"].score
        threshold = self.weights.thresholds.get("pass", 0.7)
        # `passed` is True/False whenever an overall score exists, and None only
        # when the score is unavailable. (Regression: a previous
        # `... or None` expression turned every *failing* example into None,
        # erasing the pass/fail signal.)
        passed = None if overall is None else overall >= threshold

        duration_ms = int((time.monotonic() - started) * 1000)
        record = EvaluationRecord(
            example_id=example.id,
            job_id=job_id,
            model_id=model_id,
            response_text=response,
            dimensions=dimensions,
            semantic_preservation=semantic_val,
            terminology_consistency=term_val,
            overall_score=overall,
            overall_available=overall is not None,
            passed=passed,
            error="; ".join(sorted(set(errors))) if errors else None,
            duration_ms=duration_ms,
            rubric_version=RUBRIC_VERSION,
        )
        return EngineOutput(record=record, errors=sorted(set(errors)))


def _constraint_score(example: BenchmarkExample, response: str):
    from app.evaluation.constraints import constraint_score

    return constraint_score(example, response)


def _completeness(example: BenchmarkExample, response: str) -> float:
    from app.evaluation.semantic import completeness_score

    return completeness_score(example, response)


def _requires_list(example: BenchmarkExample) -> bool:
    src = example.source_text.lower()
    return "பட்டியல்" in src or "list" in src
