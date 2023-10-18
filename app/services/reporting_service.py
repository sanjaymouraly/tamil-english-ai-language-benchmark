"""Report generation service: Markdown, HTML, JSON, CSV."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.database.models import EvaluationJob
from app.reporting import export as export_mod
from app.reporting.html import generate_html_report
from app.reporting.markdown import generate_markdown_report

REPORTS_DIR = Path("reports")


def generate_report(session, job_id: int, fmt: str) -> tuple[str, str]:
    """Generate a report for a job. Returns (content, default_filename)."""
    from app.core.errors import NotFoundError
    from app.database import crud

    job = crud.get_job(session, job_id)
    if job is None:
        raise NotFoundError(f"job {job_id} not found")
    results = crud.results_for_job(session, job_id)
    dv = _dataset_info(session, job.dataset_version_id)
    # Authoritative example_id -> category map, so reports group by real
    # category names rather than by id prefixes.
    category_by_example = {
        row.id: row.category
        for row in crud.list_examples(session, dataset_version_id=job.dataset_version_id)
    }
    # Comparison context: other jobs on the same dataset version.
    other_jobs = [
        j
        for j in crud.list_jobs(session, limit=100)
        if j.dataset_version_id == job.dataset_version_id
        and j.id != job_id
        and j.status == "completed"
    ]
    comparison = None
    if other_jobs:
        from app.services.evaluation_service import compare_jobs

        try:
            comparison = compare_jobs(
                session, [job_id] + [j.id for j in other_jobs[:3]], "overall_score"
            )
        except Exception:
            comparison = None

    manifest = export_mod.report_manifest(
        {
            "job_id": job.id,
            "name": job.name,
            "provider": job.provider,
            "model_id": job.model_id,
            "dataset_version": dv.get("version"),
            "dataset_hash": dv.get("content_hash"),
            "prompt_version": job.prompt_version,
            "rubric_version": job.rubric_version,
            "code_version": job.code_version,
        },
        len(results),
    )

    if fmt == "markdown" or fmt == "md":
        content = generate_markdown_report(job, results, dv, comparison, category_by_example)
        return content, f"reports/job_{job_id}_report.md"
    if fmt == "html":
        content = generate_html_report(job, results, dv, comparison, category_by_example)
        return content, f"reports/job_{job_id}_report.html"
    if fmt == "json":
        payload = {
            "manifest": manifest,
            "job": _job_meta(job),
            "dataset": dv,
            "results": [export_mod.results_to_rows([r])[0] for r in results],
            "comparison": comparison,
        }
        content = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        return content, f"reports/job_{job_id}_report.json"
    if fmt == "csv":
        rows = export_mod.results_to_rows(results)
        import csv
        import io

        buf = io.StringIO()
        if rows:
            fieldnames: list[str] = []
            for row in rows:
                for key in row:
                    if key not in fieldnames:
                        fieldnames.append(key)
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return buf.getvalue(), f"reports/job_{job_id}_results.csv"
    raise ValueError(f"unsupported report format: {fmt}")


def _job_meta(job: EvaluationJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "name": job.name,
        "provider": job.provider,
        "model_id": job.model_id,
        "status": job.status,
        "config": job.config_json,
        "prompt_version": job.prompt_version,
        "rubric_version": job.rubric_version,
        "code_version": job.code_version,
        "cost_usd": job.cost_usd,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error": job.error,
    }


def _dataset_info(session, dataset_version_id: int) -> dict[str, Any]:
    from app.database.models import DatasetVersion

    dv = session.get(DatasetVersion, dataset_version_id)
    if dv is None:
        return {"name": "TEB", "version": "?", "content_hash": "?", "example_count": 0}
    return {
        "name": dv.name,
        "version": dv.version,
        "content_hash": dv.content_hash,
        "example_count": dv.example_count,
        "notes": dv.notes,
    }
