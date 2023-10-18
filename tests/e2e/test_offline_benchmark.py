"""End-to-end test: full offline benchmark run + report generation.

This exercises the real workflow a user would follow, using the
deterministic mock provider (no paid API, no network).
"""

import json
from pathlib import Path

from app.core.schemas import JobConfig
from app.database.session import init_db, session_scope
from app.providers.mock import MockProvider
from app.services.evaluation_service import (
    compare_jobs,
    create_job,
    get_git_revision,
    run_job,
)
from app.services.reporting_service import generate_report


def _setup(db_session):
    from app.database import crud
    from app.datasets.loader import load_examples
    from app.datasets.validator import check_duplicates, validate_examples

    examples = load_examples(Path("benchmark/data/v1.0.0/examples.jsonl"))
    report = validate_examples(examples)
    assert report.ok, f"dataset validation failed: {report.errors}"
    assert not check_duplicates(examples)
    crud.upsert_dataset(db_session, examples, version="1.0.0")
    return examples


def test_full_offline_benchmark_run():
    init_db()
    with session_scope() as session:
        examples = _setup(session)
        config = JobConfig()
        job_id = create_job(
            session,
            "e2e offline run",
            "mock",
            "teb-mock-v1",
            config,
            code_version=get_git_revision(),
        )

    provider = MockProvider()
    summary = run_job(job_id, examples, provider, config, confirm_cost=True)

    assert summary["completed"] == len(examples)
    assert summary["errors"] == 0
    assert len(summary["results"]) == len(examples)

    # Semantic and terminology are separately recorded.
    with session_scope() as session:
        from app.database import crud

        results = crud.results_for_job(session, job_id)
        assert len(results) == len(examples)
        semantic = [r.semantic_preservation for r in results if r.semantic_preservation is not None]
        terminology = [
            r.terminology_consistency for r in results if r.terminology_consistency is not None
        ]
        assert semantic, "semantic scores must exist"
        assert terminology, "terminology scores must exist"
        assert all(0.0 <= s <= 1.0 for s in semantic)


def test_report_generation_all_formats():
    init_db()
    with session_scope() as session:
        examples = _setup(session)
        config = JobConfig()
        job_id = create_job(session, "e2e report", "mock", "teb-mock-v1", config)

    provider = MockProvider()
    run_job(job_id, examples, provider, config, confirm_cost=True)

    with session_scope() as session:
        for fmt, expected_name in [
            ("markdown", ".md"),
            ("html", ".html"),
            ("json", ".json"),
            ("csv", ".csv"),
        ]:
            content, filename = generate_report(session, job_id, fmt)
            assert content
            assert expected_name in filename
            if fmt == "json":
                payload = json.loads(content)
                assert "job" in payload
                assert "results" in payload


def test_model_comparison_paired():
    init_db()
    with session_scope() as session:
        examples = _setup(session)
        config = JobConfig(max_examples=40)
        job_a = create_job(session, "model A", "mock", "teb-mock-a", config)
        job_b = create_job(session, "model B", "mock", "teb-mock-b", config)

    provider = MockProvider()
    run_job(job_a, examples, provider, config, confirm_cost=True)
    run_job(job_b, examples, provider, config, confirm_cost=True)

    with session_scope() as session:
        report = compare_jobs(session, [job_a, job_b], "overall_score")
    assert report["common_examples"] > 0
    assert "paired_comparison" in report
    # Same mock model on same examples -> identical means
    means = [v["mean"] for v in report["per_job"].values()]
    assert len(means) == 2
