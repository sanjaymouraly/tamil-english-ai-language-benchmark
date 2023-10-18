"""TEB CLI — dataset, evaluation, comparison, reporting, diagnostics.

Usage:
    teb dataset build
    teb dataset validate benchmark/data/v1.0.0/examples.jsonl
    teb dataset import benchmark/data/v1.0.0/examples.jsonl
    teb eval run --provider mock
    teb eval report --job 1 --format html
    teb providers list
    teb doctor
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

import typer

from app.core.config import get_settings
from app.core.errors import CostLimitExceededError
from app.core.logging import configure_logging, get_logger
from app.core.schemas import JobConfig


def _configure_console_encoding() -> None:
    """Make stdout/stderr able to encode Tamil and other non-ASCII text.

    On Windows the default console code page (e.g. cp1252) cannot encode Tamil,
    which previously crashed commands while printing non-ASCII output such as
    unstable terminology concepts. We reconfigure the streams to UTF-8 and
    replace (rather than raise on) any characters the terminal still cannot
    render, so the CLI never dies because of a console limitation.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            with contextlib.suppress(Exception):
                reconfigure(encoding="utf-8", errors="replace")


_configure_console_encoding()

app = typer.Typer(
    name="teb",
    help="Tamil-English Benchmark (TEB) CLI",
    no_args_is_help=True,
)

logger = get_logger("teb.cli")

dataset_app = typer.Typer(help="Dataset operations")
eval_app = typer.Typer(help="Evaluation operations")
providers_app = typer.Typer(help="Provider operations")
annotation_app = typer.Typer(help="Annotation operations")

app.add_typer(dataset_app, name="dataset")
app.add_typer(eval_app, name="eval")
app.add_typer(providers_app, name="providers")
app.add_typer(annotation_app, name="annotation")


def _echo(msg: str) -> None:
    typer.echo(msg)


# ---------------------------------------------------------------------------
# Dataset commands
# ---------------------------------------------------------------------------


@dataset_app.command("build")
def dataset_build() -> None:
    """Build the canonical v1.0.0 dataset from seed files."""
    from app.datasets.build import build_dataset

    raise typer.Exit(build_dataset()[0])


@dataset_app.command("validate")
def dataset_validate(path: Path = typer.Argument(..., exists=True, dir_okay=False)) -> None:
    """Validate a dataset file (JSONL/JSON/CSV/Parquet)."""
    from app.datasets.loader import load_examples
    from app.datasets.validator import check_duplicates, validate_examples

    try:
        examples = load_examples(path)
    except Exception as exc:
        typer.echo(f"LOAD ERROR: {exc}", err=True)
        raise typer.Exit(2) from exc
    report = validate_examples(examples)
    dups = check_duplicates(examples)
    typer.echo(
        f"examples: {report.total}  valid: {report.valid}  errors: {len(report.errors)}  warnings: {len(report.warnings)}"
    )
    for e in report.errors:
        typer.echo(f"  ERROR [{e.example_id}] {e.rule}: {e.message}")
    for w in report.warnings[:20]:
        typer.echo(f"  WARN  [{w.example_id}] {w.rule}: {w.message}")
    if dups:
        typer.echo(f"  DUPLICATE pairs: {dups}")
    raise typer.Exit(0 if report.ok and not dups else 1)


@dataset_app.command("stats")
def dataset_stats() -> None:
    """Show dataset statistics from the database."""
    from app.database.session import init_db, session_scope
    from app.services.evaluation_service import load_dataset_examples

    init_db()
    with session_scope() as session:
        try:
            examples = load_dataset_examples(session)
        except Exception as exc:
            typer.echo(f"No dataset loaded: {exc}")
            raise typer.Exit(1) from exc
        from collections import Counter

        cats = Counter(ex.category.value for ex in examples)
        dirs = Counter(ex.direction for ex in examples)
        diffs = Counter(ex.difficulty.value for ex in examples)
        _echo(f"total examples: {len(examples)}")
        _echo("categories:")
        for cat, n in sorted(cats.items()):
            _echo(f"  {cat}: {n}")
        _echo("directions:")
        for d, n in sorted(dirs.items()):
            _echo(f"  {d}: {n}")
        _echo("difficulty:")
        for d, n in sorted(diffs.items()):
            _echo(f"  {d}: {n}")


@dataset_app.command("import")
def dataset_import(
    path: Path = typer.Argument(..., exists=True, dir_okay=False), version: str = "1.0.0"
) -> None:
    """Import a dataset file into the database."""
    from app.database.session import init_db, session_scope
    from app.datasets.loader import load_examples
    from app.datasets.validator import validate_examples

    examples = load_examples(path)
    report = validate_examples(examples)
    if not report.ok:
        for e in report.errors:
            typer.echo(f"ERROR [{e.example_id}] {e.rule}: {e.message}")
        raise typer.Exit(2)
    init_db()
    with session_scope() as session:
        from app.database import crud

        dv = crud.upsert_dataset(session, examples, version=version)
        session.commit()
        _echo(
            f"imported {len(examples)} examples as dataset v{dv.version} (hash {dv.content_hash})"
        )


@dataset_app.command("export")
def dataset_export(out: Path = typer.Argument(...), version: str | None = None) -> None:
    """Export the dataset from the database to JSONL/JSON/CSV/Parquet."""
    from app.database.session import init_db, session_scope
    from app.datasets.loader import export_examples
    from app.services.evaluation_service import load_dataset_examples

    init_db()
    with session_scope() as session:
        examples = load_dataset_examples(session, version)
        export_examples(examples, out)
        _echo(f"exported {len(examples)} examples to {out}")


# ---------------------------------------------------------------------------
# Evaluation commands
# ---------------------------------------------------------------------------


@eval_app.command("run")
def eval_run(
    provider: str = typer.Option(
        "mock", "--provider", "-p", help="Provider name (mock, offline, openai, ...)"
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Model identifier override"),
    job_name: str = typer.Option("CLI benchmark run", "--name"),
    partition: str | None = typer.Option(None, "--partition", help="train/dev/test"),
    categories: str | None = typer.Option(
        None, "--categories", help="comma-separated category filter"
    ),
    max_examples: int | None = typer.Option(None, "--max"),
    max_tokens: int | None = typer.Option(
        None, "--max-tokens", help="Completion token budget (raise for reasoning models)"
    ),
    temperature: float | None = typer.Option(None, "--temperature", help="Sampling temperature"),
    config_file: Path | None = typer.Option(
        None,
        "--config",
        exists=True,
        dir_okay=False,
        help="JSON file with a JobConfig (see configs/). CLI flags override it.",
    ),
    confirm_cost: bool = typer.Option(
        False, "--confirm-cost", help="Explicitly allow a potentially costly run"
    ),
    offline_file: Path | None = typer.Option(
        None, "--offline-file", help="JSONL of imported responses for the offline provider"
    ),
) -> None:
    """Run a benchmark evaluation job."""
    from app.database.session import init_db, session_scope
    from app.services.evaluation_service import (
        create_job,
        get_git_revision,
        load_dataset_examples,
        run_job,
        select_examples,
    )

    configure_logging(get_settings().log_level)
    settings = get_settings()
    registry = _build_registry(offline_file)

    try:
        adapter = registry.create(provider, model)
    except Exception as exc:
        typer.echo(f"PROVIDER ERROR: {exc}", err=True)
        raise typer.Exit(3) from exc

    # Base config from file (if given), then CLI flags override.
    if config_file is not None:
        config = JobConfig.model_validate(json.loads(config_file.read_text(encoding="utf-8")))
    else:
        config = JobConfig()
    if partition:
        config.partition = partition
    if categories:
        config.categories = [c.strip() for c in categories.split(",") if c.strip()]
    if max_examples:
        config.max_examples = max_examples
    if max_tokens is not None:
        config.max_tokens = max_tokens
    if temperature is not None:
        config.temperature = temperature
    init_db()
    with session_scope() as session:
        examples = load_dataset_examples(session, config.dataset_version)
        job_id = create_job(
            session,
            job_name,
            provider,
            str(model or getattr(adapter, "model", "") or provider),
            config,
            code_version=get_git_revision(),
        )

    if provider not in {"mock", "offline"}:
        estimate = None
        with contextlib.suppress(Exception):
            estimate = _estimate(adapter, examples, config)
        if estimate is not None and estimate > settings.max_cost_usd and not confirm_cost:
            typer.echo(
                f"Estimated cost ${estimate:.4f} exceeds the configured limit "
                f"${settings.max_cost_usd:.2f}. Re-run with --confirm-cost to proceed.",
                err=True,
            )
            raise typer.Exit(4)
        typer.echo(
            f"Estimated cost: ${estimate:.4f}"
            if estimate is not None
            else "Cost estimate unavailable for this model."
        )

    _echo(
        f"Starting job {job_id}: {len(select_examples(examples, config))} of "
        f"{len(examples)} examples via provider '{provider}'"
    )
    try:
        summary = run_job(job_id, examples, adapter, config, confirm_cost=confirm_cost)
    except CostLimitExceededError as exc:
        typer.echo(f"COST LIMIT EXCEEDED: {exc}", err=True)
        raise typer.Exit(5) from exc
    except Exception as exc:
        typer.echo(f"JOB FAILED: {exc}", err=True)
        raise typer.Exit(6) from exc

    _echo(
        f"Job {job_id} completed: {summary['completed']} examples, {summary['errors']} errors, cost ${summary['total_cost_usd']:.4f}"
    )
    if summary.get("terminology_consistency", {}).get("unstable_concepts"):
        _echo(
            f"Unstable terminology concepts: {list(summary['terminology_consistency']['unstable_concepts'])}"
        )


def _estimate(adapter, examples, config) -> float | None:
    from app.providers.cost import job_cost_estimate

    return job_cost_estimate(getattr(adapter, "model", ""), len(examples))


def _build_registry(offline_file: Path | None):
    from app.providers.registry import ProviderRegistry

    registry = ProviderRegistry()
    if offline_file is not None:
        registry.set_offline_file(offline_file)
    return registry


@eval_app.command("compare")
def eval_compare(
    job_ids: str = typer.Option(..., "--jobs", help="Comma-separated job IDs"),
    dimension: str = typer.Option("overall_score", "--dimension"),
) -> None:
    """Compare jobs (models) on identical samples."""
    from app.database.session import init_db, session_scope
    from app.services.evaluation_service import compare_jobs

    init_db()
    ids = [int(x.strip()) for x in job_ids.split(",")]
    with session_scope() as session:
        report = compare_jobs(session, ids, dimension)
    print(json.dumps(report, indent=2, ensure_ascii=False))


@eval_app.command("report")
def eval_report(
    job_id: int = typer.Option(..., "--job", help="Job ID"),
    fmt: str = typer.Option("markdown", "--format", "-f", help="markdown|html|json|csv"),
    out: Path | None = typer.Option(None, "--out", "-o", help="Output path"),
) -> None:
    """Generate a report for a completed job."""
    from app.database.session import init_db, session_scope
    from app.services.reporting_service import generate_report

    init_db()
    with session_scope() as session:
        content, default_name = generate_report(session, job_id, fmt)
    if out is None:
        out = Path(default_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    _echo(f"report written to {out}")


@eval_app.command("responses-import")
def eval_responses_import(
    path: Path = typer.Argument(..., exists=True, dir_okay=False),
    model_id: str = typer.Option("imported-model"),
) -> None:
    """Import model responses (JSONL: example_id, response_text) for offline evaluation."""
    import json as _json

    from app.database import crud
    from app.database.session import init_db, session_scope

    init_db()
    count = 0
    with session_scope() as session, path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = _json.loads(line)
            ex_id = rec.get("example_id") or rec.get("id")
            text = rec.get("response_text") or rec.get("response") or rec.get("text")
            if not ex_id or text is None:
                typer.echo(f"skipping malformed line: {line[:80]}", err=True)
                continue
            crud.add_model_response(session, ex_id, model_id, text)
            count += 1
    _echo(f"imported {count} responses for model '{model_id}'")


# ---------------------------------------------------------------------------
# Provider commands
# ---------------------------------------------------------------------------


@providers_app.command("list")
def providers_list() -> None:
    """List providers and their configuration status."""
    from app.providers.registry import ProviderRegistry

    registry = ProviderRegistry()
    configured = registry.list_configured()
    for name, info in configured.items():
        status = "configured" if info.get("configured") else "not configured"
        model = info.get("model", "")
        _echo(f"  {name:10s} {status:16s} model={model}")


@providers_app.command("test")
def providers_test(
    name: str = typer.Argument(...),
    model: str | None = typer.Option(None, "--model", "-m", help="Model identifier to test"),
) -> None:
    """Test connectivity to a provider."""
    from app.providers.registry import ProviderRegistry

    registry = ProviderRegistry()
    try:
        adapter = registry.create(name, model)
    except Exception as exc:
        typer.echo(f"provider '{name}' unavailable: {exc}")
        raise typer.Exit(3) from exc
    result = adapter.test_connection()
    print(json.dumps(result, indent=2, ensure_ascii=False))


@providers_app.command("discover")
def providers_discover(
    name: str = typer.Argument("ollama", help="Provider to query for available models"),
) -> None:
    """List models a provider advertises (e.g. locally installed Ollama models)."""
    from app.providers.registry import ProviderRegistry

    models = ProviderRegistry().discover_models(name)
    if not models:
        typer.echo(f"no models discovered for '{name}' (is the server running?)")
        raise typer.Exit(1)
    for m in models:
        _echo(f"  {m}")


# ---------------------------------------------------------------------------
# Annotation commands
# ---------------------------------------------------------------------------


@annotation_app.command("status")
def annotation_status() -> None:
    """Show verification status breakdown of the dataset."""
    from app.annotation.service import verification_breakdown
    from app.database.session import init_db, session_scope

    init_db()
    with session_scope() as session:
        breakdown = verification_breakdown(session)
    for status, count in sorted(breakdown.items()):
        _echo(f"  {status}: {count}")


@annotation_app.command("review")
def annotation_review(
    example_id: str = typer.Argument(..., help="Example ID, e.g. TEB-T2E-0001"),
    reviewer: str = typer.Option(..., "--reviewer", "-r", help="Reviewer name"),
    semantic: float | None = typer.Option(None, "--semantic", help="Semantic preservation (0-1)"),
    terminology: float | None = typer.Option(
        None, "--terminology", help="Terminology consistency (0-1)"
    ),
    fluency: float | None = typer.Option(None, "--fluency", help="Fluency (0-1)"),
    adequacy: float | None = typer.Option(None, "--adequacy", help="Adequacy (0-1)"),
    cultural: float | None = typer.Option(None, "--cultural", help="Cultural suitability (0-1)"),
    agrees: bool = typer.Option(True, "--agrees/--disagrees", help="Agrees with machine result"),
    status: str = typer.Option("pending", "--status", help="pending|approved|disputed"),
    notes: str = typer.Option("", "--notes", help="Free-text notes"),
) -> None:
    """Record a human review for an example."""
    from app.annotation.service import submit_review
    from app.core.errors import JobStateError
    from app.core.schemas import ReviewRecord
    from app.database.session import init_db, session_scope

    init_db()
    record = ReviewRecord.model_validate(
        {
            "example_id": example_id,
            "reviewer": reviewer,
            "semantic_score": semantic,
            "terminology_score": terminology,
            "fluency_score": fluency,
            "adequacy_score": adequacy,
            "cultural_suitability_score": cultural,
            "agrees_with_machine": agrees,
            "status": status,
            "notes": notes,
        }
    )
    try:
        with session_scope() as session:
            review = submit_review(session, record)
    except JobStateError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(5) from exc
    _echo(f"review recorded for {example_id} (review id {review.id})")


@annotation_app.command("adjudicate")
def annotation_adjudicate(
    example_id: str = typer.Argument(..., help="Example ID"),
    adjudicator: str = typer.Option(..., "--adjudicator", "-a", help="Adjudicator name"),
    decision: str = typer.Option(..., "--decision", help="uphold|override|revise"),
    notes: str = typer.Option("", "--notes", help="Free-text notes"),
) -> None:
    """Record a final adjudication for a disputed example."""
    from app.annotation.service import submit_adjudication
    from app.core.errors import JobStateError
    from app.core.schemas import AdjudicationRecord
    from app.database.session import init_db, session_scope

    init_db()
    record = AdjudicationRecord(
        example_id=example_id,
        adjudicator=adjudicator,
        decision=decision,
        final_scores={},
        notes=notes,
    )
    try:
        with session_scope() as session:
            adj = submit_adjudication(session, record)
    except JobStateError as exc:
        typer.echo(f"ERROR: {exc}", err=True)
        raise typer.Exit(5) from exc
    _echo(f"adjudication recorded for {example_id}: {adj.decision} (id {adj.id})")


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


@app.command("doctor")
def doctor() -> None:
    """System diagnostics: config, DB, dataset, providers."""
    from app.database.session import init_db, session_scope

    settings = get_settings()
    _echo("=== TEB diagnostics ===")
    _echo(f"env: {settings.env}")
    _echo(f"db path: {settings.db_path}")
    _echo(f"max cost: ${settings.max_cost_usd:.2f}")
    live = settings.live_providers_configured
    _echo(
        f"live providers configured: { {k: v for k, v in live.items() if v} or 'none (offline mode)' }"
    )

    try:
        init_db()
        with session_scope() as session:
            from sqlalchemy import text

            session.execute(text("SELECT 1"))
        _echo("database: OK")
    except Exception as exc:
        _echo(f"database: FAIL ({exc})")
        raise typer.Exit(1) from exc

    data_file = Path("benchmark/data/v1.0.0/examples.jsonl")
    if data_file.exists():
        _echo(f"dataset file: OK ({data_file})")
    else:
        _echo("dataset file: missing (run 'teb dataset build')")

    from app.providers.registry import ProviderRegistry

    registry = ProviderRegistry()
    for name in ("mock", "offline"):
        try:
            adapter = registry.create(name)
            status = adapter.test_connection()
            _echo(f"provider {name}: OK ({status})")
        except Exception as exc:
            _echo(f"provider {name}: {exc}")


@app.command("version")
def version() -> None:
    from app import __version__

    _echo(f"TEB {__version__}")


@app.command("serve")
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes (dev)"),
) -> None:
    """Start the FastAPI service (uvicorn)."""
    import uvicorn

    _echo(f"TEB API → http://{host}:{port}/docs")
    uvicorn.run("app.api.main:app", host=host, port=port, reload=reload)


@app.command("ui")
def ui(
    port: int = typer.Option(8501, "--port"),
    headless: bool = typer.Option(True, "--headless/--no-headless"),
) -> None:
    """Start the Streamlit dashboard."""
    import subprocess
    import sys

    from app.datasets.build import repo_root

    script = repo_root() / "app" / "ui" / "app.py"
    _echo(f"TEB dashboard → http://localhost:{port}")
    subprocess.run(  # noqa: S603 - fixed argv, no shell
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(script),
            "--server.port",
            str(port),
            "--server.headless",
            str(headless).lower(),
        ],
        check=False,
    )


if __name__ == "__main__":
    app()
