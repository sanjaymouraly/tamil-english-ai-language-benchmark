"""Self-contained HTML report generation.

Charts are rendered with Plotly and embedded with the plotly.js runtime
inlined, so the report is fully self-contained and renders offline.
"""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from typing import Any

import plotly.graph_objects as go

from app.database.models import EvaluationJob, EvaluationResult
from app.reporting import category_from_id as _category_from_id

_PLOTLY_COLORS = {"overall": "#2f6db3", "semantic": "#1f9d74", "terminology": "#e08a2e"}


def generate_html_report(
    job: EvaluationJob,
    results: list[EvaluationResult],
    dataset_info: dict[str, Any],
    comparison: dict[str, Any] | None = None,
    category_by_example: dict[str, str] | None = None,
) -> str:
    scores = [r for r in results if r.overall_score is not None]
    semantic = _floats([r.semantic_preservation for r in results])
    term = _floats([r.terminology_consistency for r in results])

    category_by_example = category_by_example or {}
    by_category: dict[str, list[EvaluationResult]] = {}
    for r in results:
        cat = category_by_example.get(r.example_id) or _category_from_id(r.example_id)
        by_category.setdefault(cat, []).append(r)

    cat_rows = []
    for cat in sorted(by_category):
        recs = by_category[cat]
        ov = _mean(_floats([r.overall_score for r in recs]))
        sem = _mean(_floats([r.semantic_preservation for r in recs]))
        ter = _mean(_floats([r.terminology_consistency for r in recs]))
        cat_rows.append((cat, len(recs), ov, sem, ter))

    # Plotly charts (interactive, embedded inline for offline use).
    cat_chart = _category_chart(cat_rows)
    dist_chart = _distribution_chart(_floats([r.overall_score for r in scores]))
    scatter_chart = _semantic_terminology_scatter(results)

    failures = [r for r in results if r.error]

    failure_rows = "\n".join(
        f"<tr><td>{html.escape(r.example_id)}</td><td><pre>{html.escape(r.error or '')}</pre></td>"
        f"<td><pre>{html.escape((r.response_text or '')[:200])}</pre></td></tr>"
        for r in failures[:15]
    )

    comparison_block = ""
    if comparison:
        comparison_block = f"<h2>Model comparison</h2><pre>{html.escape(json.dumps(comparison, indent=2, ensure_ascii=False))}</pre>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Evaluation Report — {html.escape(job.name)}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; margin: 0; background: #f6f7f9; color: #1b1f24; }}
  .wrap {{ max-width: 1000px; margin: 0 auto; padding: 24px; }}
  header {{ background: #12324f; color: #fff; padding: 28px 24px; border-radius: 0 0 12px 12px; }}
  header h1 {{ margin: 0 0 6px; font-size: 24px; }}
  header p {{ margin: 2px 0; font-size: 13px; opacity: .85; }}
  section {{ background: #fff; border: 1px solid #e2e6ea; border-radius: 10px; padding: 20px; margin: 18px 0; }}
  h2 {{ font-size: 18px; color: #12324f; border-bottom: 2px solid #eef1f4; padding-bottom: 6px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #edf0f3; }}
  th {{ background: #f0f4f8; }}
  .metric-cards {{ display: flex; gap: 14px; flex-wrap: wrap; }}
  .card {{ flex: 1; min-width: 160px; background: #f4f8fb; border: 1px solid #dce6ef; border-radius: 10px; padding: 14px; }}
  .card .label {{ font-size: 12px; color: #55606c; text-transform: uppercase; letter-spacing: .04em; }}
  .card .value {{ font-size: 26px; font-weight: 700; color: #12324f; margin-top: 4px; }}
  pre {{ background: #f6f8fa; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 12px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; background: #e8f0fe; color: #1a56db; }}
  .chart {{ border: 1px solid #eef1f4; border-radius: 10px; padding: 8px; margin: 8px 0; }}
  footer {{ color: #6b7280; font-size: 12px; margin: 24px 0; }}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <h1>Evaluation Report — {html.escape(job.name)}</h1>
    <p>Tamil-English Benchmark (TEB) · generated {datetime.now(UTC).isoformat(timespec="seconds")}</p>
    <p>Provider <span class="badge">{html.escape(job.provider)}</span> Model <span class="badge">{html.escape(job.model_id)}</span></p>
  </div>
</header>
<div class="wrap">
  <section>
    <h2>Reproducibility</h2>
    <table>
      <tr><th>Dataset</th><td>{html.escape(str(dataset_info.get("name", "TEB")))} v{html.escape(str(dataset_info.get("version", "?")))} (hash <code>{html.escape(str(dataset_info.get("content_hash", "?")))}</code>, {dataset_info.get("example_count", "?")} examples)</td></tr>
      <tr><th>Prompt / rubric</th><td><code>{html.escape(job.prompt_version)}</code> / <code>{html.escape(job.rubric_version)}</code></td></tr>
      <tr><th>Code version</th><td><code>{html.escape(job.code_version or "unrecorded")}</code></td></tr>
      <tr><th>Config</th><td><pre>{html.escape(json.dumps(job.config_json, sort_keys=True, ensure_ascii=False))}</pre></td></tr>
      <tr><th>Status</th><td>{html.escape(job.status)} · cost ${job.cost_usd:.4f}</td></tr>
    </table>
  </section>
  <section>
    <h2>Headline metrics</h2>
    <div class="metric-cards">
      <div class="card"><div class="label">Overall (weighted)</div><div class="value">{_fmt(_mean(_floats([r.overall_score for r in scores])))}</div><div class="label">n={len(scores)}</div></div>
      <div class="card"><div class="label">Semantic preservation</div><div class="value">{_fmt(_mean(semantic))}</div><div class="label">n={len(semantic)}</div></div>
      <div class="card"><div class="label">Terminology consistency</div><div class="value">{_fmt(_mean(term))}</div><div class="label">n={len(term)}</div></div>
    </div>
  </section>
  <section>
    <h2>Per-category performance</h2>
    <div class="chart">{cat_chart}</div>
    <table>
      <tr><th>Category</th><th>n</th><th>Overall</th><th>Semantic</th><th>Terminology</th></tr>
      {"".join(f"<tr><td>{html.escape(c)}</td><td>{n}</td><td>{_fmt(o)}</td><td>{_fmt(s)}</td><td>{_fmt(t)}</td></tr>" for c, n, o, s, t in cat_rows)}
    </table>
  </section>
  <section>
    <h2>Score distribution</h2>
    <div class="chart">{dist_chart}</div>
    <p>Semantic preservation (green) vs terminology consistency (orange) — the two
    primary axes are computed and reported <strong>separately</strong>:</p>
    <div class="chart">{scatter_chart}</div>
  </section>
  <section>
    <h2>Failure examples ({len(failures)})</h2>
    <table>
      <tr><th>Example</th><th>Error</th><th>Response</th></tr>
      {failure_rows or '<tr><td colspan="3">No failures recorded.</td></tr>'}
    </table>
  </section>
  {comparison_block}
  <footer>
    <p>Automatic scores are deterministic proxies, not human judgments. Semantic preservation and
    terminology consistency are reported separately. See docs/verification.md for limitations.</p>
  </footer>
</div>
</body>
</html>"""


def _floats(values: list[float | None]) -> list[float]:
    """Drop unavailable (None) scores, keeping only measured values."""
    return [float(v) for v in values if v is not None]


def _mean(values: list[float]) -> float | None:
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 4) if clean else None


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _category_chart(
    cat_rows: list[tuple[str, int, float | None, float | None, float | None]],
) -> str:
    """Grouped Plotly bar chart: overall / semantic / terminology per category."""
    labels = [r[0] for r in cat_rows]
    fig = go.Figure()
    for idx, (name, color) in enumerate(
        [
            ("overall", _PLOTLY_COLORS["overall"]),
            ("semantic", _PLOTLY_COLORS["semantic"]),
            ("terminology", _PLOTLY_COLORS["terminology"]),
        ]
    ):
        values = [r[2 + idx] if r[2 + idx] is not None else 0.0 for r in cat_rows]
        fig.add_bar(name=name, x=labels, y=values, marker_color=color)
    fig.update_layout(
        barmode="group",
        title="Mean score by category (overall vs semantic vs terminology)",
        yaxis=dict(title="mean score", range=[0, 1.05]),
        template="plotly_white",
        legend=dict(orientation="h", y=-0.25),
        margin=dict(l=40, r=20, t=50, b=80),
        height=420,
    )
    return fig.to_html(include_plotlyjs="inline", full_html=False, config={"displayModeBar": False})


def _distribution_chart(values: list[float]) -> str:
    """Histogram of overall scores."""
    fig = go.Figure()
    fig.add_histogram(x=values, nbinsx=20, marker_color=_PLOTLY_COLORS["overall"])
    fig.update_layout(
        title="Distribution of overall scores",
        xaxis=dict(title="overall score"),
        yaxis=dict(title="examples"),
        template="plotly_white",
        margin=dict(l=40, r=20, t=50, b=40),
        height=300,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False, config={"displayModeBar": False})


def _semantic_terminology_scatter(results: list[EvaluationResult]) -> str:
    """Scatter of semantic vs terminology per example — shows the axes are independent."""
    pts = [
        (r.semantic_preservation, r.terminology_consistency)
        for r in results
        if r.semantic_preservation is not None and r.terminology_consistency is not None
    ]
    fig = go.Figure()
    if pts:
        fig.add_trace(
            go.Scattergl(
                x=[p[0] for p in pts],
                y=[p[1] for p in pts],
                mode="markers",
                marker=dict(size=7, color=_PLOTLY_COLORS["terminology"], opacity=0.6),
                name="examples",
            )
        )
    fig.update_layout(
        title="Semantic preservation vs terminology consistency (per example)",
        xaxis=dict(title="semantic preservation", range=[0, 1.02], gridcolor="#eee"),
        yaxis=dict(title="terminology consistency", range=[0, 1.02], gridcolor="#eee"),
        template="plotly_white",
        margin=dict(l=40, r=20, t=50, b=40),
        height=340,
        showlegend=False,
    )
    return fig.to_html(include_plotlyjs=False, full_html=False, config={"displayModeBar": False})
