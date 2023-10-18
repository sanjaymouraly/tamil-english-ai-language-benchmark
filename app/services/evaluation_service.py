"""Evaluation service: shared orchestration for CLI, API, and UI."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import CostLimitExceededError, NotFoundError
from app.core.schemas import BenchmarkExample, JobConfig
from app.database import crud
from app.database.session import session_scope
from app.evaluation.engine import EvaluationEngine
from app.evaluation.runner import BenchmarkRunner
from app.providers.base import ProviderAdapter


def load_dataset_examples(
    session: Session, dataset_version: str | None = None
) -> list[BenchmarkExample]:
    """Load examples from the latest (or specified) dataset version in the DB."""
    versions = crud.dataset_versions(session)
    if dataset_version is None:
        if not versions:
            raise NotFoundError("no dataset registered; run 'teb dataset import' first")
        dv = versions[-1]
    else:
        match = next((v for v in versions if v.version == dataset_version), None)
        if match is None:
            raise NotFoundError(f"dataset version {dataset_version} not found")
        dv = match
    rows = crud.list_examples(session, dataset_version_id=dv.id)
    return [_row_to_example(row) for row in rows]


def _row_to_example(row) -> BenchmarkExample:
    from app.core.schemas import (
        Category,
        CriticalConstraint,
        Difficulty,
        GlossaryTerm,
        Provenance,
        Register,
        ScriptKind,
        VerificationStatus,
    )

    return BenchmarkExample(
        id=row.id,
        category=Category(row.category),
        task_type=row.task_type,
        direction=row.direction,
        source_text=row.source_text,
        source_script=ScriptKind(row.source_script),
        source_language=row.source_language,
        target_language=row.target_language,
        expected_behavior=row.expected_behavior,
        references=row.references or [],
        glossary=[GlossaryTerm(**g) for g in (row.glossary or [])],
        context=row.context or "",
        difficulty=Difficulty(row.difficulty),
        register_level=Register(row.register_level),
        phenomena=row.phenomena or [],
        critical_constraints=[CriticalConstraint(**c) for c in (row.critical_constraints or [])],
        provenance=Provenance(row.provenance),
        provenance_note=row.provenance_note or "",
        license=row.license,
        annotation_notes=row.annotation_notes or "",
        partition=row.partition,
        verification_status=VerificationStatus(row.verification_status),
    )


def create_job(
    session: Session,
    name: str,
    provider: str,
    model_id: str,
    config: JobConfig,
    code_version: str = "",
) -> int:  # noqa: D417
    job = crud.create_job(
        session,
        name=name,
        dataset_version_id=_dataset_version_id(session, config.dataset_version),
        provider=provider,
        model_id=model_id,
        config_json=config.model_dump(mode="json"),
        code_version=code_version,
        status="created",
        total=0,
    )
    return job.id


def _dataset_version_id(session: Session, version: str) -> int:
    dv = next((v for v in crud.dataset_versions(session) if v.version == version), None)
    if dv is None:
        raise NotFoundError(f"dataset version {version} not registered; import the dataset first")
    return dv.id


def select_examples(examples: list[BenchmarkExample], config: JobConfig) -> list[BenchmarkExample]:
    """Apply the job config's partition/category/size filters.

    ``max_examples`` draws a **seeded** random sample (``config.sampling_seed``)
    so the same config always selects the same examples.
    """
    selected = examples
    if config.partition:
        selected = [ex for ex in selected if ex.partition == config.partition]
    if config.categories:
        selected = [ex for ex in selected if ex.category.value in config.categories]
    if config.max_examples:
        import random

        rng = random.Random(config.sampling_seed)
        selected = rng.sample(selected, min(config.max_examples, len(selected)))
    return selected


def run_job(
    job_id: int,
    examples: list[BenchmarkExample],
    provider: ProviderAdapter,
    config: JobConfig,
    confirm_cost: bool = False,
    on_progress=None,
    stop_event: threading.Event | None = None,
) -> dict[str, Any]:
    engine = EvaluationEngine()
    runner = BenchmarkRunner(
        provider=provider, engine=engine, on_progress=on_progress, stop_event=stop_event
    )

    selected = select_examples(examples, config)

    with session_scope() as session:
        crud.update_job(
            session, job_id, status="running", started_at=_utcnow(), total=len(selected)
        )
        crud.add_event(
            session, job_id, "started", f"evaluating {len(selected)} examples with {provider.name}"
        )

    try:
        summary = runner.run(selected, config, job_id, confirm_cost=confirm_cost)
    except CostLimitExceededError as exc:
        with session_scope() as session:
            crud.update_job(session, job_id, status="failed", error=str(exc))
            crud.add_event(session, job_id, "cost_limit_exceeded", str(exc))
        raise
    except Exception as exc:  # keep DB consistent on unexpected failure
        with session_scope() as session:
            crud.update_job(session, job_id, status="failed", error=str(exc))
            crud.add_event(session, job_id, "failed", f"{type(exc).__name__}: {exc}")
        raise

    with session_scope() as session:
        consistency = summary.get("terminology_consistency", {})
        crud.update_job(
            session,
            job_id,
            status="completed",
            progress=summary["completed"],
            finished_at=_utcnow(),
            cost_usd=summary["total_cost_usd"],
            config_json={**config.model_dump(mode="json"), "terminology_consistency": consistency},
        )
        crud.add_event(
            session,
            job_id,
            "completed",
            f"{summary['completed']} examples, ${summary['total_cost_usd']:.4f}",
        )

    return summary


def compare_jobs(
    session: Session, job_ids: list[int], dimension: str = "overall_score"
) -> dict[str, Any]:
    """Compare jobs on identical examples (paired comparison)."""
    from app.evaluation.aggregation import paired_difference

    jobs = []
    for job_id in job_ids:
        job = crud.get_job(session, job_id)
        if job is None:
            raise NotFoundError(f"job {job_id} not found")
        jobs.append(job)

    # Map example_id -> score per job, restricted to the intersection.
    score_maps: list[dict[str, float | None]] = []
    for job in jobs:
        results = crud.results_for_job(session, job.id)
        if dimension == "overall_score":
            score_maps.append({r.example_id: r.overall_score for r in results})
        elif dimension == "semantic_preservation":
            score_maps.append({r.example_id: r.semantic_preservation for r in results})
        elif dimension == "terminology_consistency":
            score_maps.append({r.example_id: r.terminology_consistency for r in results})
        else:
            raise ValueError(f"unknown dimension: {dimension}")

    common_set = set(score_maps[0])
    for sm in score_maps[1:]:
        common_set &= set(sm)
    common_ids = sorted(common_set)

    per_job = {}
    seen_keys: set[str] = set()
    for job, sm in zip(jobs, score_maps, strict=False):
        values = [sm.get(eid) for eid in common_ids]
        clean = [v for v in values if v is not None]
        key = job.model_id or job.provider
        if key in seen_keys:  # disambiguate repeated model ids across jobs
            key = f"{key} (job {job.id})"
        seen_keys.add(key)
        per_job[key] = {
            "n": len(clean),
            "mean": round(sum(clean) / len(clean), 4) if clean else None,
        }

    pairwise = {}
    for i in range(len(jobs)):
        for j in range(i + 1, len(jobs)):
            a = [score_maps[i][eid] for eid in common_ids]
            b = [score_maps[j][eid] for eid in common_ids]
            key = (
                f"{jobs[i].model_id or jobs[i].provider} vs {jobs[j].model_id or jobs[j].provider}"
            )
            pairwise[key] = paired_difference(a, b)

    return {
        "dimension": dimension,
        "common_examples": len(common_ids),
        "per_job": per_job,
        "paired_comparison": pairwise,
    }


def job_summary(job_id: int) -> dict[str, Any]:
    with session_scope() as session:
        job = crud.get_job(session, job_id)
        if job is None:
            raise NotFoundError(f"job {job_id} not found")
        results = crud.results_for_job(session, job_id)
        return {
            "job": {
                "id": job.id,
                "name": job.name,
                "provider": job.provider,
                "model_id": job.model_id,
                "status": job.status,
                "progress": job.progress,
                "total": job.total,
                "cost_usd": job.cost_usd,
                "error": job.error,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            },
            "result_count": len(results),
        }


def get_git_revision() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return ""


def _utcnow():
    from datetime import UTC, datetime

    return datetime.now(UTC)
