"""Data schemas for the Tamil-English Benchmark (TEB).

These Pydantic models define the canonical, versioned schema for benchmark
examples, evaluation results, and annotation records. They are used by the
loader, the validator, the API, and the database layer so that every part of
the platform agrees on one definition of "an example".
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Enumerations / literals
# ---------------------------------------------------------------------------


class Category(str, Enum):
    """The 16 task families covered by the benchmark."""

    TA_TO_EN_TRANSLATION = "translation_ta_to_en"
    EN_TO_TA_TRANSLATION = "translation_en_to_ta"
    CODE_MIXED = "code_mixed_understanding"
    ROMANIZED = "romanized_transliteration"
    REGISTER = "register_formality"
    INSTRUCTION = "instruction_following"
    CUSTOMER_SUPPORT = "customer_support"
    BUSINESS_EMAIL = "business_email"
    IDIOM_CULTURE = "idiom_culture"
    AMBIGUITY = "ambiguity_context"
    TECHNICAL_TERMINOLOGY = "technical_terminology"
    SUMMARIZATION = "summarization_rewriting"
    ENTITIES_NUMBERS = "entities_numbers"
    LONG_CONTEXT = "long_context_multiturn"
    LANGUAGE_SWITCHING = "language_switching"
    SAFETY_CRITICAL = "safety_critical"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Register(str, Enum):
    FORMAL = "formal"
    INFORMAL = "informal"
    NEUTRAL = "neutral"


class Provenance(str, Enum):
    SYNTHETIC = "synthetic"
    PUBLIC_DOMAIN = "public_domain"
    LICENSED = "licensed"
    USER_CONTRIBUTED = "user_contributed"


class VerificationStatus(str, Enum):
    """How much independent checking a record has received.

    machine_validated : passed automated checks only (default for seed data)
    agent_reviewed   : reviewed by the AI maintainer agent, not a human
    human_reviewed   : reviewed by a named human reviewer
    adjudicated      : a disputed annotation was resolved by adjudication
    """

    MACHINE_VALIDATED = "machine_validated"
    AGENT_REVIEWED = "agent_reviewed"
    HUMAN_REVIEWED = "human_reviewed"
    ADJUDICATED = "adjudicated"


class ScriptKind(str, Enum):
    TAMIL = "tamil"
    LATIN = "latin"
    MIXED = "mixed"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class GlossaryTerm(BaseModel):
    """A domain term and its preferred translation, used for terminology scoring."""

    term: str = Field(min_length=1)
    translation: str = Field(min_length=1)
    language: str = Field(default="ta", description="Language of the source term ('ta' or 'en')")
    case_sensitive: bool = False

    @field_validator("language")
    @classmethod
    def _check_language(cls, v: str) -> str:
        if v not in {"ta", "en"}:
            raise ValueError("glossary term language must be 'ta' or 'en'")
        return v


class ConstraintKind(str, Enum):
    MUST_CONTAIN = "must_contain"
    MUST_NOT_CONTAIN = "must_not_contain"
    REGEX = "regex"
    NUMERIC_PRESERVATION = "numeric_preservation"
    ENTITY_PRESERVATION = "entity_preservation"


class CriticalConstraint(BaseModel):
    """A deterministically checkable requirement for an acceptable response.

    `value` may be a single string or a list of acceptable alternatives.
    """

    kind: ConstraintKind
    value: str | list[str] = Field(min_length=1)
    description: str = ""

    @property
    def alternatives(self) -> list[str]:
        if isinstance(self.value, list):
            return self.value
        return [self.value]


class BenchmarkExample(BaseModel):
    """One stable, traceable benchmark example."""

    # Seed files author the register field as ``register`` (validation alias),
    # while exports/dumps use the field name ``register_level``. Allowing
    # population by name means a JSONL/CSV round-trip preserves the value
    # instead of silently falling back to the default. (Regression: without
    # this, ``formal``/``informal`` registers were lost on every export.)
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=4, max_length=64, description="Stable identifier, e.g. TEB-T2E-0001")
    version: str = Field(default="1.0.0", description="Dataset schema version")
    category: Category
    task_type: str = Field(min_length=1)
    direction: str = Field(min_length=1, description="e.g. 'ta->en', 'en->ta', 'mixed->en'")
    source_text: str = Field(min_length=1)
    source_script: ScriptKind
    source_language: str = Field(default="ta")
    target_language: str = Field(default="en")
    expected_behavior: str = Field(min_length=1, description="What a correct response must do")
    references: list[str] = Field(
        default_factory=list, min_length=1, description="Acceptable reference outputs"
    )
    glossary: list[GlossaryTerm] = Field(default_factory=list)
    context: str = ""
    difficulty: Difficulty
    register_level: Register = Field(
        default=Register.NEUTRAL, validation_alias="register", serialization_alias="register"
    )
    phenomena: list[str] = Field(default_factory=list, description="Linguistic phenomenon tags")
    critical_constraints: list[CriticalConstraint] = Field(default_factory=list)
    provenance: Provenance = Provenance.SYNTHETIC
    provenance_note: str = ""
    license: str = "CC-BY-4.0"
    annotation_notes: str = ""
    partition: Literal["train", "dev", "test"] | None = None
    verification_status: VerificationStatus = VerificationStatus.MACHINE_VALIDATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        if not v.startswith("TEB-"):
            raise ValueError("example id must start with 'TEB-'")
        if not v.replace("-", "").isalnum() or any(c.islower() for c in v[4:]):
            raise ValueError("example id must be uppercase alphanumerics separated by dashes")
        return v

    @field_validator("references")
    @classmethod
    def _check_references(cls, v: list[str]) -> list[str]:
        if not any(r.strip() for r in v):
            raise ValueError("at least one non-empty reference is required")
        return v

    def content_hash(self) -> str:
        """Stable hash of the substantive fields (identity for dedup)."""
        payload = {
            "category": self.category.value,
            "direction": self.direction,
            "source_text": self.source_text,
            "references": sorted(self.references),
            "difficulty": self.difficulty.value,
        }
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]


class ExampleIngest(BaseModel):
    """Wrapper used when importing raw records."""

    examples: list[BenchmarkExample]
    source: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# Evaluation results
# ---------------------------------------------------------------------------


class MetricResult(BaseModel):
    name: str
    score: float | None = Field(
        default=None, description="0..1 when computable; null = unavailable"
    )
    available: bool = True
    evidence: dict[str, object] = Field(default_factory=dict)
    method: str = "deterministic"
    notes: str = ""


class DimensionScore(BaseModel):
    """One quality dimension with its score, provenance and explanation."""

    dimension: str
    score: float | None = None
    available: bool = True
    provenance: Literal["deterministic", "reference_similarity", "llm_judge", "human"] = (
        "deterministic"
    )
    evidence: list[str] = Field(default_factory=list)
    rubric_version: str = "rubric-v1"
    confidence: float | None = None
    notes: str = ""


class EvaluationRecord(BaseModel):
    """Complete evaluation outcome for one example and one model response."""

    example_id: str
    job_id: str | None = None
    model_id: str = ""
    response_text: str = ""
    dimensions: dict[str, DimensionScore] = Field(default_factory=dict)
    semantic_preservation: float | None = None
    terminology_consistency: float | None = None
    overall_score: float | None = None
    overall_available: bool = True
    passed: bool | None = None
    error: str | None = None
    duration_ms: int = 0
    judge_model: str | None = None
    rubric_version: str = "rubric-v1"


class JobConfig(BaseModel):
    """Configurable evaluation settings persisted with every job."""

    dataset_version: str = "1.0.0"
    partition: str | None = None
    categories: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "semantic_preservation": 0.45,
            "terminology_consistency": 0.20,
            "entity_number_preservation": 0.10,
            "constraint_satisfaction": 0.15,
            "script_validity": 0.05,
            "completeness": 0.05,
        }
    )
    thresholds: dict[str, float] = Field(default_factory=lambda: {"pass": 0.7})
    include_judge: bool = False
    judge_model: str | None = None
    judge_rubric_version: str = "rubric-v1"
    sampling_seed: int = 42
    max_examples: int | None = None
    # Decoding settings, persisted with the job for reproducibility.
    # max_tokens defaults high enough for "reasoning" models (e.g. qwen3)
    # that emit a thinking trace before the answer.
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1)


# ---------------------------------------------------------------------------
# Annotation / human review
# ---------------------------------------------------------------------------


class ReviewRecord(BaseModel):
    example_id: str
    reviewer: str
    semantic_score: float | None = None
    terminology_score: float | None = None
    fluency_score: float | None = None
    adequacy_score: float | None = None
    cultural_suitability_score: float | None = None
    agrees_with_machine: bool | None = None
    status: Literal["pending", "approved", "disputed"] = "pending"
    notes: str = ""
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AdjudicationRecord(BaseModel):
    example_id: str
    adjudicator: str
    decision: str
    final_scores: dict[str, float] = Field(default_factory=dict)
    notes: str = ""
    adjudicated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
