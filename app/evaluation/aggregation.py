"""Aggregation of evaluation results with bootstrap confidence intervals."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import numpy as np

from app.core.schemas import EvaluationRecord


@dataclass
class GroupStats:
    count: int
    mean: float | None
    std: float | None
    ci_low: float | None
    ci_high: float | None
    ci_method: str = "bootstrap_percentile_95"
    values: list[float] = field(default_factory=list)


def _bootstrap_ci(
    values: list[float], n_boot: int = 2000, seed: int = 42
) -> tuple[float, float] | None:
    """Bootstrap 95% percentile confidence interval for the mean."""
    if len(values) < 5:
        # Too few samples for a stable CI: report the plain mean only.
        return None
    rng = random.Random(seed)
    arr = np.array(values, dtype=float)
    means = np.empty(n_boot)
    for i in range(n_boot):
        sample = rng.choices(arr.tolist(), k=len(arr))
        means[i] = float(np.mean(sample))
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def group_stats(values: list[float | None]) -> GroupStats:
    clean = [v for v in values if v is not None]
    if not clean:
        return GroupStats(count=len(values), mean=None, std=None, ci_low=None, ci_high=None)
    arr = np.array(clean, dtype=float)
    mean = float(arr.mean())
    std = float(arr.std(ddof=1)) if len(clean) > 1 else 0.0
    ci = _bootstrap_ci(clean)
    return GroupStats(
        count=len(clean),
        mean=round(mean, 4),
        std=round(std, 4),
        ci_low=round(ci[0], 4) if ci else None,
        ci_high=round(ci[1], 4) if ci else None,
        values=clean,
    )


def aggregate_records(records: list[EvaluationRecord], key_fn) -> dict[str, dict[str, GroupStats]]:
    """Group records by a key function and compute per-dimension stats."""
    groups: dict[str, list[EvaluationRecord]] = {}
    for rec in records:
        groups.setdefault(key_fn(rec), []).append(rec)
    out: dict[str, dict[str, GroupStats]] = {}
    for key, recs in groups.items():
        dims = ("overall_score", "semantic_preservation", "terminology_consistency")
        stats = {}
        for dim in dims:
            values = [getattr(r, dim) for r in recs]
            stats[dim] = group_stats(values)
        out[key] = stats
    return out


def paired_difference(
    a_scores: list[float | None], b_scores: list[float | None], seed: int = 42
) -> dict[str, object]:
    """Paired bootstrap comparison of two models on identical examples."""
    pairs = [
        (a, b) for a, b in zip(a_scores, b_scores, strict=False) if a is not None and b is not None
    ]
    if len(pairs) < 5:
        return {
            "n": len(pairs),
            "mean_diff": None,
            "ci_low": None,
            "ci_high": None,
            "ci_excludes_zero": None,
            "note": "too few paired examples for a bootstrap interval (need >= 5)",
        }
    diffs = np.array([a - b for a, b in pairs], dtype=float)
    mean_diff = float(diffs.mean())
    rng = random.Random(seed)
    boot = np.empty(2000)
    for i in range(2000):
        sample = rng.choices(diffs.tolist(), k=len(diffs))
        boot[i] = float(np.mean(sample))
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    return {
        "n": len(pairs),
        "mean_diff": round(mean_diff, 4),
        "ci_low": round(lo, 4),
        "ci_high": round(hi, 4),
        # Deliberately NOT named "significant": a bootstrap CI that excludes zero
        # is descriptive evidence, not a formal hypothesis test.
        "ci_excludes_zero": bool(lo > 0 or hi < 0),
        "note": "descriptive paired bootstrap; not a formal significance test",
    }


def effect_size(a: list[float], b: list[float]) -> float | None:
    """Cohen's d for two independent groups (descriptive)."""
    if len(a) < 2 or len(b) < 2:
        return None
    na, nb = len(a), len(b)
    va, vb = float(np.var(a, ddof=1)), float(np.var(b, ddof=1))
    pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    if pooled == 0:
        return 0.0
    return round((float(np.mean(a)) - float(np.mean(b))) / pooled, 4)
