"""Dataset loading and export for JSONL, JSON, CSV, and Parquet formats."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.schemas import BenchmarkExample
from app.core.security import safe_filename

SUPPORTED_EXTENSIONS = {".jsonl", ".json", ".csv", ".parquet"}


def load_examples(path: Path) -> list[BenchmarkExample]:
    """Load benchmark examples from a JSON/JSONL/CSV/Parquet file."""
    if not path.exists():
        raise FileNotFoundError(f"dataset file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        records = _read_jsonl(path)
    elif suffix == ".json":
        records = _read_json(path)
    elif suffix == ".csv":
        records = _read_csv(path)
    elif suffix == ".parquet":
        records = _read_parquet(path)
    else:
        raise ValueError(f"unsupported dataset extension: {suffix}")
    examples = []
    for i, rec in enumerate(records):
        try:
            examples.append(BenchmarkExample.model_validate(rec))
        except Exception as exc:  # re-raise with position info
            raise ValueError(f"record {i} in {path.name} failed validation: {exc}") from exc
    return examples


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_no} of {path.name}: {exc}") from exc
    return records


def _read_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        for key in ("examples", "data", "records"):
            if isinstance(data.get(key), list):
                return data[key]
        raise ValueError("JSON dataset must be a list or contain an 'examples' list")
    if isinstance(data, list):
        return data
    raise ValueError("unsupported JSON dataset structure")


def _read_csv(path: Path) -> list[dict[str, Any]]:
    df = pd.read_csv(path)
    return _records_from_dataframe(df)


def _read_parquet(path: Path) -> list[dict[str, Any]]:
    df = pd.read_parquet(path)
    return _records_from_dataframe(df)


def _records_from_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        record: dict[str, Any] = {}
        for col in df.columns:
            value = row[col]
            if pd.isna(value):
                continue
            if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
                with contextlib.suppress(json.JSONDecodeError):
                    value = json.loads(value)
            record[col] = value
        records.append(record)
    return records


def export_examples(examples: list[BenchmarkExample], path: Path) -> None:
    """Export examples to JSONL, JSON, CSV, or Parquet based on extension."""
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_filename(path.name)
    records = [ex.model_dump(mode="json") for ex in examples]
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        with path.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    elif suffix == ".json":
        path.write_text(
            json.dumps({"examples": records}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    elif suffix == ".csv":
        df = pd.DataFrame([_flatten_record(r) for r in records])
        df.to_csv(path, index=False, encoding="utf-8")
    elif suffix == ".parquet":
        df = pd.DataFrame([_flatten_record(r) for r in records])
        df.to_parquet(path, index=False)
    else:
        raise ValueError(f"unsupported export extension: {suffix}")


def _flatten_record(rec: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested lists so CSV/Parquet columns stay simple."""
    flat: dict[str, Any] = {}
    for key, value in rec.items():
        if isinstance(value, list):
            flat[key] = json.dumps(value, ensure_ascii=False)
        else:
            flat[key] = value
    return flat


#: Fields that record *ingestion* metadata rather than benchmark content.
#: They are deliberately excluded from the content hash so that the hash
#: identifies the dataset's substantive content and is stable across rebuilds
#: and across machines (see ``dataset_content_hash``).
VOLATILE_FIELDS = frozenset({"created_at"})


def canonical_record(record: dict[str, Any]) -> dict[str, Any]:
    """Project a record onto its substantive, hash-stable content fields."""
    return {k: v for k, v in record.items() if k not in VOLATILE_FIELDS}


def dataset_content_hash(examples: list[BenchmarkExample]) -> str:
    """Stable hash of the dataset's substantive content.

    Volatile ingestion metadata (``created_at``) is excluded so the hash is a
    deterministic function of the benchmark content alone. This makes the hash
    reproducible across rebuilds and machines, and safe to use as a dataset
    identity for benchmark snapshots.
    """
    import hashlib

    payload = json.dumps(
        [canonical_record(ex.model_dump(mode="json")) for ex in examples],
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]
