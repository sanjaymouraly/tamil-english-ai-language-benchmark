"""SQLAlchemy ORM models for the TEB platform."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DatasetVersion(Base):
    __tablename__ = "dataset_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="TEB")
    version: Mapped[str] = mapped_column(String(32))
    content_hash: Mapped[str] = mapped_column(String(64))
    example_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    examples: Mapped[list[Example]] = relationship(
        back_populates="dataset_version", cascade="all, delete-orphan"
    )


class Example(Base):
    __tablename__ = "example"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dataset_version.id"), index=True
    )
    category: Mapped[str] = mapped_column(String(60))
    task_type: Mapped[str] = mapped_column(String(60))
    direction: Mapped[str] = mapped_column(String(40))
    source_text: Mapped[str] = mapped_column(Text)
    source_script: Mapped[str] = mapped_column(String(10))
    source_language: Mapped[str] = mapped_column(String(10), default="ta")
    target_language: Mapped[str] = mapped_column(String(10), default="en")
    expected_behavior: Mapped[str] = mapped_column(Text)
    references: Mapped[dict] = mapped_column(JSON, default=list)
    glossary: Mapped[dict] = mapped_column(JSON, default=list)
    context: Mapped[str] = mapped_column(Text, default="")
    difficulty: Mapped[str] = mapped_column(String(10))
    register_level: Mapped[str] = mapped_column(String(10), default="neutral")
    phenomena: Mapped[dict] = mapped_column(JSON, default=list)
    critical_constraints: Mapped[dict] = mapped_column(JSON, default=list)
    provenance: Mapped[str] = mapped_column(String(20), default="synthetic")
    provenance_note: Mapped[str] = mapped_column(Text, default="")
    license: Mapped[str] = mapped_column(String(40), default="CC-BY-4.0")
    annotation_notes: Mapped[str] = mapped_column(Text, default="")
    partition: Mapped[str | None] = mapped_column(String(10), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="machine_validated")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    dataset_version: Mapped[DatasetVersion] = relationship(back_populates="examples")
    reviews: Mapped[list[AnnotationReview]] = relationship(
        back_populates="example", cascade="all, delete-orphan"
    )
    results: Mapped[list[EvaluationResult]] = relationship(back_populates="example")


class EvaluationJob(Base):
    __tablename__ = "evaluation_job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    dataset_version_id: Mapped[int] = mapped_column(Integer, ForeignKey("dataset_version.id"))
    provider: Mapped[str] = mapped_column(String(40))
    model_id: Mapped[str] = mapped_column(String(120))
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_version: Mapped[str] = mapped_column(String(40), default="prompt-v1")
    rubric_version: Mapped[str] = mapped_column(String(40), default="rubric-v1")
    code_version: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(
        String(20), default="created"
    )  # created|running|completed|failed|interrupted
    progress: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[list[EvaluationResult]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    events: Mapped[list[JobEvent]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("evaluation_job.id"), index=True)
    example_id: Mapped[str] = mapped_column(String(64), ForeignKey("example.id"), index=True)
    model_id: Mapped[str] = mapped_column(String(120))
    response_text: Mapped[str] = mapped_column(Text)
    scores_json: Mapped[dict] = mapped_column(JSON, default=dict)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_preservation: Mapped[float | None] = mapped_column(Float, nullable=True)
    terminology_consistency: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1/0/None
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    judge_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rubric_version: Mapped[str] = mapped_column(String(40), default="rubric-v1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    job: Mapped[EvaluationJob] = relationship(back_populates="results")
    example: Mapped[Example] = relationship(back_populates="results")


class ModelResponse(Base):
    __tablename__ = "model_response"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    example_id: Mapped[str] = mapped_column(String(64), index=True)
    model_id: Mapped[str] = mapped_column(String(120))
    response_text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40), default="import")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class AnnotationReview(Base):
    __tablename__ = "annotation_review"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    example_id: Mapped[str] = mapped_column(String(64), ForeignKey("example.id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(120))
    semantic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    terminology_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fluency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    adequacy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cultural_suitability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    agrees_with_machine: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1/0/None
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    example: Mapped[Example] = relationship(back_populates="reviews")


class Adjudication(Base):
    __tablename__ = "adjudication"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    example_id: Mapped[str] = mapped_column(String(64), index=True)
    adjudicator: Mapped[str] = mapped_column(String(120))
    decision: Mapped[str] = mapped_column(String(40))
    final_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")
    adjudicated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class JobEvent(Base):
    __tablename__ = "job_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("evaluation_job.id"), index=True)
    event: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    job: Mapped[EvaluationJob] = relationship(back_populates="events")


class ProviderConfig(Base):
    """Non-secret provider configuration (keys live in env only)."""

    __tablename__ = "provider_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), unique=True)
    base_url: Mapped[str] = mapped_column(String(300), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    enabled: Mapped[int] = mapped_column(Integer, default=0)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
