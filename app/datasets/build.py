"""Deterministic dataset build pipeline.

This lives inside the ``app`` package (rather than only in ``scripts/``) so it
is importable from the installed ``teb`` console script and from a container,
where ``scripts/`` is not on ``sys.path``. ``scripts/build_dataset.py`` is a thin
wrapper around :func:`build_dataset`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.core.schemas import BenchmarkExample
from app.datasets.loader import dataset_content_hash, export_examples
from app.datasets.partitions import assign_partitions, partition_stats
from app.datasets.registry import DatasetRegistry
from app.datasets.validator import check_duplicates, validate_examples

#: Default dataset release version.
DEFAULT_VERSION = "1.0.0"

#: Fixed release timestamp stamped onto every record of this version.
#: Using a constant (instead of ``datetime.now()``) keeps the exported files
#: byte-for-byte reproducible across rebuilds and machines. The substantive
#: content hash ignores this field entirely.
RELEASE_TIMESTAMP = datetime(2026, 10, 17, tzinfo=UTC)


def repo_root() -> Path:
    """Best-effort location of the repository root (contains ``benchmark/``)."""
    candidate = Path(__file__).resolve().parents[2]
    if (candidate / "benchmark" / "seed").is_dir():
        return candidate
    # Fallback: current working directory (e.g. a checkout invoked from elsewhere).
    return Path.cwd()


def build_dataset(
    version: str = DEFAULT_VERSION,
    seed_dir: Path | None = None,
    data_dir: Path | None = None,
    registry_dir: Path | None = None,
    verbose: bool = True,
) -> tuple[int, dict]:
    """Build, validate and export the dataset.

    Returns ``(exit_code, manifest)``. ``exit_code`` is 0 on success, 1 on
    validation errors, 2 when no seed files are found.
    """
    root = repo_root()
    seed_dir = Path(seed_dir) if seed_dir else root / "benchmark" / "seed"
    data_dir = Path(data_dir) if data_dir else root / "benchmark" / "data" / f"v{version}"
    registry_dir = Path(registry_dir) if registry_dir else root / "data" / "registry"

    def _log(msg: str) -> None:
        if verbose:
            print(msg)

    seed_files = sorted(seed_dir.glob("*.json"))
    if not seed_files:
        print(f"No seed files found in {seed_dir}")
        return 2, {}

    examples: list[BenchmarkExample] = []
    for path in seed_files:
        records = json.loads(path.read_text(encoding="utf-8"))
        for rec in records:
            examples.append(BenchmarkExample.model_validate(rec))

    _log(f"Loaded {len(examples)} examples from {len(seed_files)} seed files.")

    # Pin ingestion metadata so rebuilds are byte-identical (see RELEASE_TIMESTAMP).
    for ex in examples:
        ex.created_at = RELEASE_TIMESTAMP

    report = validate_examples(examples)
    for e in report.errors:
        print(f"ERROR [{e.example_id}] {e.rule}: {e.message}")
    for w in report.warnings:
        print(f"WARN  [{w.example_id}] {w.rule}: {w.message}")
    if report.errors:
        print(f"Build failed with {len(report.errors)} error(s).")
        return 1, {}

    dups = check_duplicates(examples)
    if dups:
        for a, b in dups:
            print(f"ERROR duplicate source text: {a} <-> {b}")
        return 1, {}

    examples = assign_partitions(examples)
    stats = partition_stats(examples)

    data_dir.mkdir(parents=True, exist_ok=True)
    export_examples(examples, data_dir / "examples.jsonl")
    export_examples(examples, data_dir / "examples.csv")
    export_examples(examples, data_dir / "examples.parquet")

    categories: dict[str, int] = {}
    for ex in examples:
        categories[ex.category.value] = categories.get(ex.category.value, 0) + 1

    manifest = {
        "name": "Tamil-English Benchmark (TEB)",
        "version": version,
        "example_count": len(examples),
        "content_hash": dataset_content_hash(examples),
        "partitions": stats,
        "categories": categories,
        "license": "CC-BY-4.0",
        "provenance": "All records authored synthetically for this benchmark (no copyrighted corpus).",
        "verification_status": "machine_validated (no human review yet)",
        "created_by": "TEB build pipeline",
        "released_at": RELEASE_TIMESTAMP.isoformat(),
    }
    (data_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Register in the live registry copy.
    DatasetRegistry(registry_dir).register(
        "TEB", version, examples, notes="Initial release built from seed files."
    )

    _log(f"Build OK: {len(examples)} examples, hash={manifest['content_hash']}, partitions={stats}")
    _log(f"Categories: {len(categories)}")
    for cat, count in sorted(categories.items()):
        _log(f"  {cat}: {count}")
    return 0, manifest
