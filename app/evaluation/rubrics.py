"""Evaluation rubrics: dimension definitions, scales, and versions."""

from __future__ import annotations

from dataclasses import dataclass

RUBRIC_VERSION = "rubric-v1"


@dataclass(frozen=True)
class RubricDimension:
    name: str
    scale_max: float
    description: str
    method: str  # deterministic | reference_similarity | llm_judge | human
    available_by_default: bool


DIMENSIONS: dict[str, RubricDimension] = {
    "semantic_preservation": RubricDimension(
        name="semantic_preservation",
        scale_max=1.0,
        description="Are the intended meaning, critical facts, negation, modality, quantities, and temporal information retained? (Deterministic proxy; LLM-judge replaceable.)",
        method="deterministic",
        available_by_default=True,
    ),
    "terminology_consistency": RubricDimension(
        name="terminology_consistency",
        scale_max=1.0,
        description="Are predefined domain terms translated consistently, within and across examples?",
        method="deterministic",
        available_by_default=True,
    ),
    "constraint_satisfaction": RubricDimension(
        name="constraint_satisfaction",
        scale_max=1.0,
        description="Fraction of critical meaning constraints satisfied (facts that must survive or be absent).",
        method="deterministic",
        available_by_default=True,
    ),
    "entity_number_preservation": RubricDimension(
        name="entity_number_preservation",
        scale_max=1.0,
        description="Are numbers, dates, times, units, and named entities preserved exactly?",
        method="deterministic",
        available_by_default=True,
    ),
    "script_validity": RubricDimension(
        name="script_validity",
        scale_max=1.0,
        description="Does the response use the expected script (Tamil/Latin/mixed) without mojibake?",
        method="deterministic",
        available_by_default=True,
    ),
    "completeness": RubricDimension(
        name="completeness",
        scale_max=1.0,
        description="Is the response non-empty and of sensible length relative to references?",
        method="deterministic",
        available_by_default=True,
    ),
    "transliteration_accuracy": RubricDimension(
        name="transliteration_accuracy",
        scale_max=1.0,
        description="For romanized-Tamil tasks: Tamil-script rendering and romanization fidelity.",
        method="deterministic",
        available_by_default=False,  # only for ROM category
    ),
    "fluency": RubricDimension(
        name="fluency",
        scale_max=1.0,
        description="Is the response free of mechanical defects? Heuristic-only without a judge; NULL unless computed.",
        method="deterministic",
        available_by_default=True,
    ),
    "adequacy": RubricDimension(
        name="adequacy",
        scale_max=1.0,
        description="Does the response convey the full meaning of the source? Requires an LLM judge or human review.",
        method="llm_judge",
        available_by_default=False,
    ),
    "naturalness": RubricDimension(
        name="naturalness",
        scale_max=1.0,
        description="Does the response read naturally to a native speaker? Requires human review or judge.",
        method="llm_judge",
        available_by_default=False,
    ),
    "cultural_suitability": RubricDimension(
        name="cultural_suitability",
        scale_max=1.0,
        description="Are honorifics, tone, and cultural references appropriate? Requires human review or judge.",
        method="llm_judge",
        available_by_default=False,
    ),
    "code_mix_appropriateness": RubricDimension(
        name="code_mix_appropriateness",
        scale_max=1.0,
        description="Is code-mixing handled appropriately (when present)? Requires judge or human.",
        method="llm_judge",
        available_by_default=False,
    ),
    "hallucination": RubricDimension(
        name="hallucination",
        scale_max=1.0,
        description="Does the response add unsupported content? Requires judge or human; deterministic signals limited to invented numbers.",
        method="llm_judge",
        available_by_default=False,
    ),
    "instruction_following": RubricDimension(
        name="instruction_following",
        scale_max=1.0,
        description="Are explicit format/length/language instructions followed?",
        method="deterministic",
        available_by_default=True,
    ),
}


def rubric_prompt(dimension: str, example_source: str, references: list[str], response: str) -> str:
    """Build a judge prompt for LLM-based dimensions."""
    return (
        f"You are a careful bilingual Tamil-English evaluator.\n"
        f"Evaluate ONLY the dimension: {dimension}.\n"
        f"Source text: {example_source}\n"
        f"Acceptable reference(s): {references}\n"
        f"Model response: {response}\n"
        f'Reply in JSON exactly like this: {{"score": <0.0 to 1.0>, "reasoning": "...", "evidence": ["..."]}}\n'
        f"Score 1.0 = excellent, 0.5 = partially correct, 0.0 = failure. Base the score only on the dimension."
    )


JUDGE_PROMPT_VERSION = "judge-prompt-v1"
