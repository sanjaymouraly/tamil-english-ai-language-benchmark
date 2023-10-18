#!/usr/bin/env python3
"""Build the canonical TEB dataset from the seed files.

Thin wrapper around :func:`app.datasets.build.build_dataset` so the pipeline can
be run either as ``python scripts/build_dataset.py`` or via ``teb dataset build``.

Reads ``benchmark/seed/*.json``, validates every record, checks for accidental
duplicates and reference leakage, assigns deterministic train/dev/test
partitions, and writes:

  benchmark/data/v<version>/examples.jsonl
  benchmark/data/v<version>/examples.csv
  benchmark/data/v<version>/examples.parquet
  benchmark/data/v<version>/manifest.json

Exit code 1 if any validation error is found (warnings are printed but do not
fail the build), 2 if no seed files are found.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.datasets.build import build_dataset  # noqa: E402


def main() -> int:
    exit_code, _manifest = build_dataset()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
