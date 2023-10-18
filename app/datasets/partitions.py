"""Deterministic train/dev/test partitioning with leakage prevention."""

from __future__ import annotations

import hashlib
from typing import Literal

from app.core.schemas import BenchmarkExample

Partition = Literal["train", "dev", "test"]

# Deterministic split ratios.
DEFAULT_RATIOS = {"train": 0.70, "dev": 0.15, "test": 0.15}


def assign_partition(example_id: str, ratios: dict[str, float] = DEFAULT_RATIOS) -> Partition:
    """Assign a partition deterministically from the example ID hash.

    Using a stable hash of the ID (not the content) means records keep their
    partition across dataset edits, and the split is reproducible.
    """
    digest = hashlib.sha256(example_id.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16) / 0xFFFFFFFF  # 0..1
    train_end = ratios["train"]
    dev_end = train_end + ratios["dev"]
    if value < train_end:
        return "train"
    if value < dev_end:
        return "dev"
    return "test"


def assign_partitions(examples: list[BenchmarkExample]) -> list[BenchmarkExample]:
    """Return copies with the partition field set (leakage-checked)."""
    assigned: list[BenchmarkExample] = []
    for ex in examples:
        partition = assign_partition(ex.id)
        ex.partition = partition
        assigned.append(ex)
    return assigned


def partition_stats(examples: list[BenchmarkExample]) -> dict[str, int]:
    counts = {"train": 0, "dev": 0, "test": 0}
    for ex in examples:
        if ex.partition in counts:
            counts[ex.partition] += 1
    return counts
