"""Markdown report generation from stored evaluation results."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.database.models import EvaluationJob, EvaluationResult
from app.reporting import category_from_id as _category_from_id


def generate_markdown_report(
    job: EvaluationJob,
    results: list[EvaluationResult],
    dataset_info: dict[str, Any],
    comparison: dict[str, Any] | None = None,
    category_by_example: dict[str, str] | None = None,
) -> str:
    lines: list[str] = []
    lines.append(f"# Evaluation Report — {job.name}")
    lines.append("")
    lines.append(f"*Generated: {datetime.now(UTC).isoformat(timespec='seconds')}*")
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append(
        f"- Dataset: {dataset_info.get('name', 'TEB')} v{dataset_info.get('version', '?')} "
        f"(content hash `{dataset_info.get('content_hash', '?')}`, {dataset_info.get('example_count', '?')} examples)"
    )
    lines.append(f"- Provider: **{job.provider}** · Model: **{job.model_id}**")
    lines.append(
        f"- Prompt version: `{job.prompt_version}` · Rubric version: `{job.rubric_version}`"
    )
    lines.append(f"- Code version: `{job.code_version or 'unrecorded'}`")
    lines.append(f"- Job status: {job.status} · Cost: ${job.cost_usd:.4f}")
    lines.append(f"- Config: `{json.dumps(job.config_json, sort_keys=True)}`")
    lines.append("")

    scores = [r for r in results if r.overall_score is not None]
    semantic = _floats([r.semantic_preservation for r in results])
    term = _floats([r.terminology_consistency for r in results])

    lines.append("## Headline metrics")
    lines.append("")
    lines.append("| Metric | n | Mean |")
    lines.append("|---|---|---|")
    lines.append(
        f"| Overall (weighted) | {len(scores)} | {_mean(_floats([r.overall_score for r in scores])) if scores else 'n/a'} |"
    )
    lines.append(
        f"| **Semantic preservation** | {len(semantic)} | {_mean(semantic) if semantic else 'n/a'} |"
    )
    lines.append(
        f"| **Terminology consistency** | {len(term)} | {_mean(term) if term else 'n/a'} |"
    )
    lines.append("")

    # Per-category breakdown (use the authoritative category when available).
    category_by_example = category_by_example or {}
    by_category: dict[str, list[EvaluationResult]] = {}
    for r in results:
        cat = category_by_example.get(r.example_id) or _category_from_id(r.example_id)
        by_category.setdefault(cat, []).append(r)
    lines.append("## Per-category overall score")
    lines.append("")
    lines.append("| Category | n | Mean overall | Mean semantic | Mean terminology |")
    lines.append("|---|---|---|---|---|")
    for cat in sorted(by_category):
        recs = by_category[cat]
        ov = _mean([r.overall_score for r in recs if r.overall_score is not None])
        sem = _mean([r.semantic_preservation for r in recs if r.semantic_preservation is not None])
        ter = _mean(
            [r.terminology_consistency for r in recs if r.terminology_consistency is not None]
        )
        lines.append(f"| {cat} | {len(recs)} | {ov} | {sem} | {ter} |")
    lines.append("")

    # Failure examples.
    failures = [r for r in results if r.error]
    lines.append(f"## Failure examples ({len(failures)})")
    lines.append("")
    for r in failures[:10]:
        lines.append(f"### {r.example_id}")
        lines.append(f"- Error: {r.error}")
        lines.append(f"- Response: ```{r.response_text[:300]}```")
        lines.append("")

    if comparison:
        lines.append("## Model comparison")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(comparison, indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

    lines.append("---")
    lines.append(
        "_This report was generated from stored results. Automatic scores are "
        "deterministic proxies; they are not human judgments. See the "
        "methodology documentation for limitations._"
    )
    return "\n".join(lines)


def _floats(values: list[float | None]) -> list[float]:
    """Drop unavailable (None) scores, keeping only measured values."""
    return [float(v) for v in values if v is not None]


def _mean(values: list[float]) -> str:
    if not values:
        return "n/a"
    return f"{sum(values) / len(values):.4f}"
