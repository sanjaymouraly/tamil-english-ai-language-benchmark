"""Database CRUD operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.schemas import BenchmarkExample
from app.database.models import (
    Adjudication,
    AnnotationReview,
    DatasetVersion,
    EvaluationJob,
    EvaluationResult,
    Example,
    JobEvent,
    ModelResponse,
    ProviderConfig,
)

# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


def upsert_dataset(
    session: Session,
    examples: list[BenchmarkExample],
    name: str = "TEB",
    version: str = "1.0.0",
    notes: str = "",
) -> DatasetVersion:
    existing = session.execute(
        select(DatasetVersion).where(DatasetVersion.version == version)
    ).scalar_one_or_none()
    from app.datasets.loader import dataset_content_hash

    content_hash = dataset_content_hash(examples)
    if existing:
        session.query(Example).filter(Example.dataset_version_id == existing.id).delete()
        existing.example_count = len(examples)
        existing.notes = notes
        existing.content_hash = content_hash
        dv = existing
    else:
        dv = DatasetVersion(
            name=name,
            version=version,
            content_hash=content_hash,
            example_count=len(examples),
            notes=notes,
        )
        session.add(dv)
        session.flush()
    for ex in examples:
        session.add(_example_row(ex, dv.id))
    session.flush()
    return dv


def _example_row(ex: BenchmarkExample, dataset_version_id: int) -> Example:
    return Example(
        id=ex.id,
        dataset_version_id=dataset_version_id,
        category=ex.category.value,
        task_type=ex.task_type,
        direction=ex.direction,
        source_text=ex.source_text,
        source_script=ex.source_script.value,
        source_language=ex.source_language,
        target_language=ex.target_language,
        expected_behavior=ex.expected_behavior,
        references=ex.references,
        glossary=[g.model_dump() for g in ex.glossary],
        context=ex.context,
        difficulty=ex.difficulty.value,
        register_level=ex.register_level.value,
        phenomena=ex.phenomena,
        critical_constraints=[c.model_dump() for c in ex.critical_constraints],
        provenance=ex.provenance.value,
        provenance_note=ex.provenance_note,
        license=ex.license,
        annotation_notes=ex.annotation_notes,
        partition=ex.partition,
        verification_status=ex.verification_status.value,
    )


def list_examples(
    session: Session,
    dataset_version_id: int | None = None,
    category: str | None = None,
    partition: str | None = None,
) -> list[Example]:
    stmt = select(Example)
    if dataset_version_id is not None:
        stmt = stmt.where(Example.dataset_version_id == dataset_version_id)
    if category:
        stmt = stmt.where(Example.category == category)
    if partition:
        stmt = stmt.where(Example.partition == partition)
    return list(session.execute(stmt).scalars().all())


def get_example(session: Session, example_id: str) -> Example | None:
    return session.get(Example, example_id)


def dataset_versions(session: Session) -> list[DatasetVersion]:
    return list(session.execute(select(DatasetVersion).order_by(DatasetVersion.id)).scalars().all())


# ---------------------------------------------------------------------------
# Jobs & results
# ---------------------------------------------------------------------------


def create_job(session: Session, **kwargs: Any) -> EvaluationJob:
    job = EvaluationJob(**kwargs)
    session.add(job)
    session.flush()
    return job


def get_job(session: Session, job_id: int) -> EvaluationJob | None:
    return session.get(EvaluationJob, job_id)


def list_jobs(session: Session, limit: int = 50) -> list[EvaluationJob]:
    return list(
        session.execute(select(EvaluationJob).order_by(EvaluationJob.id.desc()).limit(limit))
        .scalars()
        .all()
    )


def update_job(session: Session, job_id: int, **kwargs: Any) -> None:
    job = get_job(session, job_id)
    if job is None:
        raise KeyError(f"job {job_id} not found")
    for key, value in kwargs.items():
        setattr(job, key, value)
    session.flush()


def add_result(session: Session, record: dict[str, Any]) -> EvaluationResult:
    row = EvaluationResult(**record)
    session.add(row)
    session.flush()
    return row


def results_for_job(session: Session, job_id: int) -> list[EvaluationResult]:
    return list(
        session.execute(select(EvaluationResult).where(EvaluationResult.job_id == job_id))
        .scalars()
        .all()
    )


def results_for_model(session: Session, model_id: str) -> list[EvaluationResult]:
    return list(
        session.execute(select(EvaluationResult).where(EvaluationResult.model_id == model_id))
        .scalars()
        .all()
    )


def all_results(session: Session) -> list[EvaluationResult]:
    return list(session.execute(select(EvaluationResult)).scalars().all())


def add_model_response(
    session: Session, example_id: str, model_id: str, response_text: str, source: str = "import"
) -> ModelResponse:
    row = ModelResponse(
        example_id=example_id, model_id=model_id, response_text=response_text, source=source
    )
    session.add(row)
    session.flush()
    return row


def model_responses(session: Session, model_id: str | None = None) -> list[ModelResponse]:
    stmt = select(ModelResponse)
    if model_id:
        stmt = stmt.where(ModelResponse.model_id == model_id)
    return list(session.execute(stmt).scalars().all())


# ---------------------------------------------------------------------------
# Annotation / review
# ---------------------------------------------------------------------------


def add_review(session: Session, review: dict[str, Any]) -> AnnotationReview:
    row = AnnotationReview(**review)
    session.add(row)
    session.flush()
    return row


def reviews_for_example(session: Session, example_id: str) -> list[AnnotationReview]:
    return list(
        session.execute(select(AnnotationReview).where(AnnotationReview.example_id == example_id))
        .scalars()
        .all()
    )


def all_reviews(session: Session) -> list[AnnotationReview]:
    return list(session.execute(select(AnnotationReview)).scalars().all())


def add_adjudication(session: Session, adj: dict[str, Any]) -> Adjudication:
    row = Adjudication(**adj)
    session.add(row)
    session.flush()
    return row


def adjudications_for_example(session: Session, example_id: str) -> list[Adjudication]:
    return list(
        session.execute(select(Adjudication).where(Adjudication.example_id == example_id))
        .scalars()
        .all()
    )


def add_event(session: Session, job_id: int, event: str, message: str = "") -> JobEvent:
    row = JobEvent(job_id=job_id, event=event, message=message)
    session.add(row)
    session.flush()
    return row


# ---------------------------------------------------------------------------
# Provider config
# ---------------------------------------------------------------------------


def upsert_provider_config(session: Session, provider: str, **kwargs: Any) -> ProviderConfig:
    row = session.execute(
        select(ProviderConfig).where(ProviderConfig.provider == provider)
    ).scalar_one_or_none()
    if row is None:
        row = ProviderConfig(provider=provider)
        session.add(row)
    for key, value in kwargs.items():
        setattr(row, key, value)
    row.updated_at = datetime.now(UTC)
    session.flush()
    return row


def provider_configs(session: Session) -> list[ProviderConfig]:
    return list(session.execute(select(ProviderConfig)).scalars().all())
