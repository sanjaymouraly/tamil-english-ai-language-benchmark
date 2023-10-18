"""Result export helpers (CSV / JSON) with reproducible hashing."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from app.database.models import EvaluationResult


def results_to_rows(results: list[EvaluationResult]) -> list[dict[str, Any]]:
    rows = []
    for r in results:
        row = {
            "example_id": r.example_id,
            "job_id": r.job_id,
            "model_id": r.model_id,
            "overall_score": r.overall_score,
            "semantic_preservation": r.semantic_preservation,
            "terminology_consistency": r.terminology_consistency,
            "passed": r.passed,
            "error": r.error,
            "duration_ms": r.duration_ms,
            "response_text": r.response_text,
        }
        if r.scores_json:
            for dim, payload in r.scores_json.items():
                row[f"dim_{dim}"] = payload.get("score") if isinstance(payload, dict) else payload
        rows.append(row)
    return rows


def export_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Union all keys across rows (different examples have different
    # dimension scores, e.g. transliteration only for romanized tasks).
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def export_json(payload: dict[str, Any], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def report_manifest(job_meta: dict[str, Any], result_count: int) -> dict[str, Any]:
    return {
        "job": job_meta,
        "result_count": result_count,
        "generated_at": _utc_now(),
        "report_version": "report-v1",
    }


def _utc_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
