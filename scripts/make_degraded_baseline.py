#!/usr/bin/env python3
"""Generate a synthetic "degraded baseline" responses file for demos.

Purpose: the **Model Comparison** workflow needs at least two completed jobs.
Rather than call a paid model (which the repo must not require), this script
takes a completed job's stored responses and applies *deterministic*,
clearly-synthetic degradations to a subset, then writes a JSONL file suitable
for the offline provider.

The result is a deliberately **weaker, synthetic** baseline. It exists to
exercise the comparison UI and the paired-comparison statistics — it is **not**
a measurement of any real model, and any report built from it must say so.

Usage:

    python scripts/make_degraded_baseline.py --job 1 --out examples/synthetic-degraded-responses.jsonl

Degradations applied (chosen deterministically from the example id):

* numeric error  — the first digit in the response is incremented (mod 10);
* omission       — the response is truncated to ~60% of its length;
* word drop      — the first three words are removed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.database import crud  # noqa: E402
from app.database.session import init_db, session_scope  # noqa: E402


def _bucket(example_id: str, salt: str) -> int:
    digest = hashlib.sha256(f"{example_id}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16)


def degrade(example_id: str, text: str) -> str:
    """Apply one deterministic degradation to a response."""
    if not text.strip():
        return text
    bucket = _bucket(example_id, "degrade") % 10

    if bucket < 4:
        # numeric error: bump the first digit
        def _bump(match: re.Match[str]) -> str:
            digit = match.group(0)
            return str((int(digit) + 1) % 10)

        changed = re.sub(r"\d", _bump, text, count=1)
        if changed != text:
            return changed

    if bucket < 7:
        # omission: truncate
        cut = max(1, int(len(text) * 0.6))
        return text[:cut].rstrip()

    # word drop: remove the first three words
    parts = text.split()
    return " ".join(parts[3:]) if len(parts) > 4 else text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=int, required=True, help="source job id (completed)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-label", default="synthetic-degraded-v1", help="model id to record")
    args = parser.parse_args()

    init_db()
    with session_scope() as session:
        results = crud.results_for_job(session, args.job)
        if not results:
            print(f"job {args.job} has no results", file=sys.stderr)
            return 1
        records = [
            {"example_id": r.example_id, "response_text": degrade(r.example_id, r.response_text)}
            for r in results
        ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(
        f"wrote {len(records)} synthetic-degraded responses to {args.out} "
        f"(label '{args.model_label}')"
    )
    print("NOTE: synthetic fixture for demoing model comparison — NOT a real model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
