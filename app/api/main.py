"""FastAPI application: programmatic evaluation endpoints.

Run with: uvicorn app.api.main:app --reload
The API is optional; the CLI and Streamlit UI work without it.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.core.errors import CostLimitExceededError, NotFoundError, ProviderError
from app.core.logging import configure_logging, get_logger
from app.core.schemas import JobConfig
from app.database.session import init_db, session_scope

logger = get_logger("teb.api")

app = FastAPI(
    title="Tamil-English Benchmark (TEB) API",
    description="Programmatic evaluation endpoints for the Tamil-English AI Language Quality Benchmark.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    configure_logging()
    init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _paginate(items: list[Any], offset: int, limit: int) -> dict[str, Any]:
    return {
        "total": len(items),
        "offset": offset,
        "limit": limit,
        "items": items[offset : offset + limit],
    }


# ---------------------------------------------------------------------------
# Health & diagnostics
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "teb-api"}


@app.get("/diagnostics")
def diagnostics() -> dict[str, Any]:
    from app.core.config import get_settings
    from app.services.evaluation_service import get_git_revision

    settings = get_settings()
    return {
        "settings": settings.redacted_view(),
        "git_revision": get_git_revision(),
        "live_providers": settings.live_providers_configured,
    }


# ---------------------------------------------------------------------------
# Datasets & examples
# ---------------------------------------------------------------------------


@app.get("/datasets")
def list_datasets() -> list[dict[str, Any]]:
    from app.database import crud

    with session_scope() as session:
        return [
            {
                "id": dv.id,
                "name": dv.name,
                "version": dv.version,
                "content_hash": dv.content_hash,
                "example_count": dv.example_count,
                "created_at": dv.created_at.isoformat() if dv.created_at else None,
            }
            for dv in crud.dataset_versions(session)
        ]


@app.get("/examples")
def list_examples(
    category: str | None = None,
    partition: str | None = None,
    difficulty: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    from app.database import crud

    if limit > 500:
        raise HTTPException(status_code=400, detail="limit must be <= 500")
    with session_scope() as session:
        rows = crud.list_examples(session, category=category, partition=partition)
        if difficulty:
            rows = [r for r in rows if r.difficulty == difficulty]
        items = [_example_public(r) for r in rows]
    return _paginate(items, offset, limit)


@app.get("/examples/{example_id}")
def get_example(example_id: str) -> dict[str, Any]:
    from app.database import crud

    with session_scope() as session:
        row = crud.get_example(session, example_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"example {example_id} not found")
        return _example_public(row)


def _example_public(row) -> dict[str, Any]:
    return {
        "id": row.id,
        "category": row.category,
        "task_type": row.task_type,
        "direction": row.direction,
        "source_text": row.source_text,
        "source_script": row.source_script,
        "expected_behavior": row.expected_behavior,
        "references": row.references,
        "glossary": row.glossary,
        "context": row.context,
        "difficulty": row.difficulty,
        "register": row.register_level,
        "phenomena": row.phenomena,
        "critical_constraints": row.critical_constraints,
        "provenance": row.provenance,
        "license": row.license,
        "partition": row.partition,
        "verification_status": row.verification_status,
    }


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------


class JobCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    provider: str = Field(min_length=1)
    model: str | None = None
    config: JobConfig = Field(default_factory=JobConfig)
    confirm_cost: bool = False


class JobRunResponse(BaseModel):
    job_id: int
    summary: dict[str, Any] | None = None
    error: str | None = None


@app.post("/jobs", response_model=JobRunResponse)
def create_and_run_job(req: JobCreateRequest) -> JobRunResponse:
    """Create an evaluation job and run it to completion (synchronous)."""
    from app.providers.registry import ProviderRegistry
    from app.services.evaluation_service import create_job, load_dataset_examples, run_job

    try:
        registry = ProviderRegistry()
        adapter = registry.create(req.provider, req.model)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with session_scope() as session:
        try:
            examples = load_dataset_examples(session, req.config.dataset_version)
        except NotFoundError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        from app.services.evaluation_service import get_git_revision

        job_id = create_job(
            session,
            req.name,
            req.provider,
            str(req.model or getattr(adapter, "model", "") or req.provider),
            req.config,
            code_version=get_git_revision(),
        )

    try:
        summary = run_job(job_id, examples, adapter, req.config, confirm_cost=req.confirm_cost)
    except CostLimitExceededError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("job %s failed", job_id)
        raise HTTPException(status_code=500, detail=f"job failed: {exc}") from exc

    return JobRunResponse(job_id=job_id, summary=summary)


@app.get("/jobs")
def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    from app.database import crud

    with session_scope() as session:
        jobs = crud.list_jobs(session, limit=limit)
        return [
            {
                "id": j.id,
                "name": j.name,
                "provider": j.provider,
                "model_id": j.model_id,
                "status": j.status,
                "progress": j.progress,
                "total": j.total,
                "cost_usd": j.cost_usd,
                "error": j.error,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]


@app.get("/jobs/{job_id}")
def get_job(job_id: int) -> dict[str, Any]:
    from app.services.evaluation_service import job_summary

    try:
        return job_summary(job_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/jobs/{job_id}/results")
def get_job_results(job_id: int, offset: int = 0, limit: int = 100) -> dict[str, Any]:
    from app.core.errors import NotFoundError as NF
    from app.database import crud

    with session_scope() as session:
        job = crud.get_job(session, job_id)
        if job is None:
            raise NF(f"job {job_id} not found")
        results = crud.results_for_job(session, job_id)
        items = [
            {
                "example_id": r.example_id,
                "model_id": r.model_id,
                "response_text": r.response_text,
                "overall_score": r.overall_score,
                "semantic_preservation": r.semantic_preservation,
                "terminology_consistency": r.terminology_consistency,
                "passed": r.passed,
                "error": r.error,
                "scores": r.scores_json,
            }
            for r in results
        ]
    return _paginate(items, offset, limit)


# ---------------------------------------------------------------------------
# Comparison & reports
# ---------------------------------------------------------------------------


@app.get("/compare")
def compare(
    job_ids: str = Query(..., description="comma-separated job IDs"),
    dimension: str = "overall_score",
) -> dict[str, Any]:
    from app.services.evaluation_service import compare_jobs

    try:
        ids = [int(x.strip()) for x in job_ids.split(",")]
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="job_ids must be comma-separated integers"
        ) from exc
    with session_scope() as session:
        try:
            return compare_jobs(session, ids, dimension)
        except (NotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


class ReportRequest(BaseModel):
    format: str = Field(default="markdown", pattern="^(markdown|md|html|json|csv)$")


@app.post("/jobs/{job_id}/report")
def generate_job_report(job_id: int, req: ReportRequest) -> dict[str, Any]:
    from app.services.reporting_service import generate_report

    with session_scope() as session:
        try:
            content, default_name = generate_report(session, job_id, req.format)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job_id, "format": req.format, "filename": default_name, "content": content}


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


@app.get("/providers")
def list_providers() -> dict[str, Any]:
    from app.providers.registry import ProviderRegistry

    return ProviderRegistry().list_configured()


class ProviderTestRequest(BaseModel):
    provider: str = Field(min_length=1)
    model: str | None = None


@app.post("/providers/test")
def test_provider(req: ProviderTestRequest) -> dict[str, Any]:
    from app.providers.registry import ProviderRegistry

    try:
        adapter = ProviderRegistry().create(req.provider, req.model)
        return adapter.test_connection()
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Offline response import
# ---------------------------------------------------------------------------


class ResponseImportRequest(BaseModel):
    model_id: str = Field(min_length=1)
    responses: list[dict[str, str]] = Field(min_length=1)


@app.post("/responses/import")
def import_responses(req: ResponseImportRequest) -> dict[str, Any]:
    """Import pre-collected model responses for offline evaluation."""
    from app.database import crud

    count = 0
    with session_scope() as session:
        for item in req.responses:
            ex_id = item.get("example_id")
            text = item.get("response_text")
            if not ex_id or text is None:
                raise HTTPException(
                    status_code=400, detail="each response needs 'example_id' and 'response_text'"
                )
            crud.add_model_response(session, ex_id, req.model_id, text)
            count += 1
    return {"imported": count, "model_id": req.model_id}


# ---------------------------------------------------------------------------
# Annotation & adjudication
# ---------------------------------------------------------------------------


class ReviewRequest(BaseModel):
    example_id: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    semantic_score: float | None = None
    terminology_score: float | None = None
    fluency_score: float | None = None
    adequacy_score: float | None = None
    cultural_suitability_score: float | None = None
    agrees_with_machine: bool = True
    status: str = Field(default="pending", pattern="^(pending|approved|disputed)$")
    notes: str = ""


class AdjudicationRequest(BaseModel):
    example_id: str = Field(min_length=1)
    adjudicator: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    final_scores: dict[str, float] = Field(default_factory=dict)
    notes: str = ""


@app.get("/annotations/status")
def annotation_status() -> dict[str, Any]:
    from app.annotation.service import verification_breakdown

    with session_scope() as session:
        return verification_breakdown(session)


@app.post("/annotations/review")
def submit_review(req: ReviewRequest) -> dict[str, Any]:
    """Record one reviewer's independent scores for an example."""
    from app.annotation.service import submit_review as _submit
    from app.core.errors import JobStateError
    from app.core.schemas import ReviewRecord

    try:
        with session_scope() as session:
            review = _submit(session, ReviewRecord(**req.model_dump()))
    except JobStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "review_id": review.id}


@app.post("/annotations/adjudicate")
def submit_adjudication(req: AdjudicationRequest) -> dict[str, Any]:
    """Record a final adjudicated decision for a disputed example."""
    from app.annotation.service import submit_adjudication as _submit
    from app.core.errors import JobStateError
    from app.core.schemas import AdjudicationRecord

    try:
        with session_scope() as session:
            adj = _submit(session, AdjudicationRecord(**req.model_dump()))
    except JobStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "adjudication_id": adj.id, "decision": adj.decision}


@app.get("/annotations/{example_id}")
def annotation_detail(example_id: str) -> dict[str, Any]:
    """Combined human-review state for one example."""
    from app.annotation.service import example_annotation_status

    with session_scope() as session:
        return example_annotation_status(session, example_id)


@app.get("/openapi.json", include_in_schema=False)
def openapi_spec() -> dict[str, Any]:
    return app.openapi()
