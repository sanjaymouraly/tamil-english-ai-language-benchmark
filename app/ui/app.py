"""Tamil-English Benchmark (TEB) — Streamlit dashboard.

Run with: streamlit run app/ui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is importable when launched directly with
# `streamlit run app/ui/app.py`. Streamlit (like any `python script.py` run)
# puts the *script's* directory first on sys.path, so `import app` would
# resolve to this very file (app/ui/app.py) instead of the `app` package and
# fail with "No module named 'app.core'; 'app' is not a package".
#
# The project root may already be on sys.path but *behind* the script
# directory, so it is not enough to check for membership — we must move it to
# the front and remove the shadowing directory.
_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_DIR = Path(__file__).resolve().parent


def _bootstrap_sys_path() -> None:
    def _is_script_dir(entry: str) -> bool:
        try:
            return Path(entry or ".").resolve() == _SCRIPT_DIR
        except OSError:  # pragma: no cover - defensive
            return False

    root = str(_ROOT)
    sys.path[:] = [p for p in sys.path if not _is_script_dir(p) and p != root]
    sys.path.insert(0, root)


_bootstrap_sys_path()

import threading

import plotly.graph_objects as go
import streamlit as st

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.session import init_db, session_scope

st.set_page_config(
    page_title="TEB — Tamil-English Benchmark",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  .block-container {padding-top: 2rem;}
  .tamil { font-family: 'Noto Sans Tamil', 'Latha', 'Nirmala UI', sans-serif; }
  div[data-testid="stDataFrame"] { font-size: 13px; }
  .demo-banner { background: #fff4e5; border: 1px solid #f0c36d;
    padding: 8px 12px; border-radius: 8px; color: #7a4d00; }
  .metric-card { background: #f4f8fb; border: 1px solid #dce6ef;
    border-radius: 10px; padding: 14px; text-align: center; }
</style>
""",
    unsafe_allow_html=True,
)

configure_logging(get_settings().log_level)
init_db()

PAGES = [
    "Overview",
    "Dataset Explorer",
    "Evaluation",
    "Results Explorer",
    "Model Comparison",
    "Error Analysis",
    "Annotation Workspace",
    "Providers",
    "Reports",
]


def main() -> None:
    st.sidebar.title("📊 TEB")
    st.sidebar.caption("Tamil-English AI Language Quality Benchmark")
    page = st.sidebar.radio("Navigation", PAGES)
    st.sidebar.markdown("---")
    st.sidebar.caption("Dataset v1.0.0 · 160 examples")

    if page == "Overview":
        render_overview()
    elif page == "Dataset Explorer":
        render_dataset()
    elif page == "Evaluation":
        render_evaluation()
    elif page == "Results Explorer":
        render_results()
    elif page == "Model Comparison":
        render_comparison()
    elif page == "Error Analysis":
        render_error_analysis()
    elif page == "Annotation Workspace":
        render_annotation()
    elif page == "Providers":
        render_providers()
    elif page == "Reports":
        render_reports()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _load_examples() -> list[dict]:
    with session_scope() as session:
        from app.database import crud

        rows = crud.list_examples(session)
        return [
            {
                "id": r.id,
                "category": r.category,
                "direction": r.direction,
                "source_text": r.source_text,
                "difficulty": r.difficulty,
                "register": r.register_level,
                "partition": r.partition,
                "verification_status": r.verification_status,
            }
            for r in rows
        ]


def _load_jobs() -> list[dict]:
    with session_scope() as session:
        from app.database import crud

        return [
            {
                "id": j.id,
                "name": j.name,
                "provider": j.provider,
                "model_id": j.model_id,
                "status": j.status,
                "progress": j.progress,
                "total": j.total,
                "cost_usd": j.cost_usd,
            }
            for j in crud.list_jobs(session, limit=100)
        ]


def _load_results(job_id: int) -> list[dict]:
    with session_scope() as session:
        from app.database import crud

        rows = crud.results_for_job(session, job_id)
        return [
            {
                "example_id": r.example_id,
                "model_id": r.model_id,
                "response_text": r.response_text,
                "overall_score": r.overall_score,
                "semantic_preservation": r.semantic_preservation,
                "terminology_consistency": r.terminology_consistency,
                "passed": r.passed,
                "error": r.error,
                "scores": r.scores_json or {},
            }
            for r in rows
        ]


def _demo_banner(provider: str) -> None:
    if provider in {"mock", "offline"}:
        st.markdown(
            f'<div class="demo-banner">⚠️ <b>Demo data</b> — results from the <i>{provider}</i> provider are '
            "simulated/imported and are <b>not</b> measured model performance.</div>",
            unsafe_allow_html=True,
        )


def _mean(values: list) -> float | None:
    clean = [v for v in values if isinstance(v, (int, float))]
    return round(sum(clean) / len(clean), 4) if clean else None


def _bar_figure(counts: dict[str, int], title: str) -> go.Figure:
    """Simple Plotly bar chart from a {label: count} mapping."""
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    fig = go.Figure(
        go.Bar(x=[k for k, _ in items], y=[v for _, v in items], marker_color="#2f6db3")
    )
    fig.update_layout(
        title=title,
        xaxis=dict(categoryorder="total descending"),
        yaxis=dict(title="count"),
        template="plotly_white",
        height=320,
        margin=dict(l=40, r=20, t=50, b=120),
    )
    return fig


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def render_overview() -> None:
    st.title("Tamil-English AI Language Quality Benchmark")
    st.markdown(
        "Evaluate how accurately, naturally, and consistently AI models handle Tamil, English, Tanglish, and romanized Tamil."
    )

    examples = _load_examples()
    jobs = _load_jobs()

    if not examples:
        st.info(
            "No dataset loaded yet. Run `teb dataset build && teb dataset import benchmark/data/v1.0.0/examples.jsonl`."
        )
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Benchmark examples", len(examples))
    c2.metric("Task categories", len({e["category"] for e in examples}))
    c3.metric("Evaluation jobs", len(jobs))
    completed = sum(1 for j in jobs if j["status"] == "completed")
    c4.metric("Completed jobs", completed)

    st.markdown("### Dataset composition")
    col1, col2 = st.columns(2)
    with col1:
        from collections import Counter

        cat_counts = Counter(e["category"] for e in examples)
        st.plotly_chart(_bar_figure(cat_counts, "Examples per category"), width="stretch")
    with col2:
        diff_counts = Counter(e["difficulty"] for e in examples)
        st.plotly_chart(_bar_figure(diff_counts, "Examples per difficulty"), width="stretch")

    st.markdown("### Language directions")
    dir_counts = Counter(e["direction"] for e in examples)
    st.write(dir_counts)

    st.markdown("### Recent jobs")
    if jobs:
        import pandas as pd

        st.dataframe(pd.DataFrame(jobs).head(10), width="stretch")
    else:
        st.caption("No jobs yet — run an evaluation from the Evaluation page.")

    st.markdown("### Verification status")
    from app.annotation.service import verification_breakdown

    with session_scope() as session:
        breakdown = verification_breakdown(session)
    st.json(breakdown)
    st.caption(
        "Most seed records are machine_validated. Human review is recorded via the Annotation Workspace."
    )


def render_dataset() -> None:
    st.title("Dataset Explorer")
    examples = _load_examples()
    if not examples:
        st.info("No dataset loaded.")
        return

    import pandas as pd

    df = pd.DataFrame(examples)
    st.sidebar.markdown("### Filters")
    cat_filter = st.sidebar.multiselect("Category", sorted(df["category"].unique()))
    diff_filter = st.sidebar.multiselect("Difficulty", sorted(df["difficulty"].unique()))
    part_filter = st.sidebar.multiselect(
        "Partition", sorted(str(p) for p in df["partition"].unique())
    )
    search = st.sidebar.text_input("Search source text")

    filtered = df
    if cat_filter:
        filtered = filtered[filtered["category"].isin(cat_filter)]
    if diff_filter:
        filtered = filtered[filtered["difficulty"].isin(diff_filter)]
    if part_filter:
        filtered = filtered[filtered["partition"].astype(str).isin(part_filter)]
    if search:
        filtered = filtered[filtered["source_text"].str.contains(search, case=False, na=False)]

    st.markdown(f"**{len(filtered)}** of {len(df)} examples")
    st.dataframe(filtered, width="stretch", height=480)

    st.markdown("### Example detail")
    if not filtered.empty:
        selected = st.selectbox("Example ID", filtered["id"].tolist())
        row = filtered[filtered["id"] == selected].iloc[0]
        st.markdown(
            f"**{row['id']}** · {row['category']} · {row['direction']} · {row['difficulty']}"
        )
        st.markdown("**Source text:**")
        st.markdown(
            f'<p class="tamil" style="font-size:16px">{row["source_text"]}</p>',
            unsafe_allow_html=True,
        )
        with session_scope() as session:
            from app.database import crud

            full = crud.get_example(session, selected)
            if full:
                st.markdown("**Acceptable references:**")
                for ref in full.references:
                    st.markdown(f"- {ref}")
                if full.glossary:
                    st.markdown("**Glossary:**")
                    for g in full.glossary:
                        st.markdown(f"- `{g['term']}` → `{g['translation']}`")
                if full.critical_constraints:
                    st.markdown("**Critical constraints:**")
                    for c in full.critical_constraints:
                        st.markdown(f"- {c['kind']}: {c['value']} — {c.get('description', '')}")


def render_evaluation() -> None:
    st.title("Evaluation")
    examples = _load_examples()
    if not examples:
        st.info("No dataset loaded.")
        return

    st.markdown("### Configure evaluation")
    col1, col2 = st.columns(2)
    with col1:
        provider = st.selectbox(
            "Provider",
            [
                "mock",
                "offline",
                "openai",
                "anthropic",
                "openrouter",
                "ollama",
                "lmstudio",
                "custom",
            ],
        )
        model = st.text_input("Model (leave blank for provider default)")
        partition = st.selectbox("Partition", ["all", "train", "dev", "test"])
    with col2:
        categories = st.multiselect(
            "Categories (empty = all)", sorted({e["category"] for e in examples})
        )
        max_examples = st.number_input("Max examples (0 = all)", min_value=0, value=0)
        job_name = st.text_input("Job name", "Dashboard evaluation run")

    config = {
        "dataset_version": "1.0.0",
        "partition": None if partition == "all" else partition,
        "categories": categories,
        "max_examples": int(max_examples) if max_examples > 0 else None,
        "weights": {
            "semantic_preservation": 0.45,
            "terminology_consistency": 0.20,
            "entity_number_preservation": 0.10,
            "constraint_satisfaction": 0.15,
            "script_validity": 0.05,
            "completeness": 0.05,
        },
        "thresholds": {"pass": 0.7},
    }

    if provider in {"mock", "offline"}:
        st.markdown(
            '<div class="demo-banner">⚠️ Demo mode — results are simulated or imported, not live model performance.</div>',
            unsafe_allow_html=True,
        )

    if st.button("▶ Run evaluation", type="primary"):
        if provider not in {"mock", "offline"} and not st.session_state.get("cost_confirmed"):
            st.warning("This will call a paid API. Confirm the estimated cost first.")
        _start_job(provider, model, job_name, config)

    if "job_thread" in st.session_state:
        progress = st.session_state.get("job_progress", {})
        st.progress(min(progress.get("completed", 0) / max(progress.get("total", 1), 1)))
        st.caption(
            f"completed {progress.get('completed', 0)}/{progress.get('total', 0)} · errors {progress.get('errors', 0)} · cost ${progress.get('cost_usd', 0):.4f}"
        )
        if not st.session_state["job_thread"].is_alive():
            st.session_state.pop("job_thread", None)
            st.rerun()

    st.markdown("### Job history")
    jobs = _load_jobs()
    if jobs:
        import pandas as pd

        st.dataframe(pd.DataFrame(jobs), width="stretch")


def _start_job(provider: str, model: str, name: str, config: dict) -> None:
    from app.core.schemas import JobConfig
    from app.providers.registry import ProviderRegistry
    from app.services.evaluation_service import create_job, load_dataset_examples, run_job

    registry = ProviderRegistry()
    try:
        adapter = registry.create(provider, model or None)
    except Exception as exc:
        st.error(f"Provider error: {exc}")
        return

    def _worker():
        with session_scope() as session:
            examples = load_dataset_examples(session, config.get("dataset_version", "1.0.0"))
            job_id = create_job(
                session,
                name,
                provider,
                model or getattr(adapter, "model", provider),
                JobConfig(**config),
            )
        try:
            run_job(job_id, examples, adapter, JobConfig(**config), confirm_cost=True)
        except Exception as exc:
            st.session_state["job_error"] = str(exc)

    if "job_thread" not in st.session_state or not st.session_state["job_thread"].is_alive():
        thread = threading.Thread(target=_worker, daemon=True)
        st.session_state["job_thread"] = thread
        st.session_state["job_progress"] = {
            "completed": 0,
            "total": 0,
            "errors": 0,
            "cost_usd": 0.0,
        }
        thread.start()
        st.rerun()


def render_results() -> None:
    st.title("Results Explorer")
    jobs = _load_jobs()
    if not jobs:
        st.info("No jobs yet.")
        return
    # Prefer completed jobs: defaulting to an in-progress job (which has no
    # persisted results yet) would show an empty page for no good reason.
    completed = [j for j in jobs if j["status"] == "completed"]
    options = completed or jobs
    if not completed:
        st.info("No completed jobs yet — showing all jobs.")
    job_options = {f"#{j['id']} {j['name']} ({j['model_id']})": j["id"] for j in options}
    selected = st.selectbox("Job", list(job_options))
    job_id = job_options[selected]
    job = next(j for j in jobs if j["id"] == job_id)
    _demo_banner(job["provider"])

    results = _load_results(job_id)
    if not results:
        st.info("No results yet.")
        return

    import pandas as pd

    df = pd.DataFrame(results)
    st.markdown("### Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Overall mean", _mean(df["overall_score"].dropna()))
    c2.metric("Semantic mean", _mean(df["semantic_preservation"].dropna()))
    c3.metric("Terminology mean", _mean(df["terminology_consistency"].dropna()))

    # The two primary axes are separate — plot them against each other.
    if {"semantic_preservation", "terminology_consistency"}.issubset(df.columns):
        pts = df[["semantic_preservation", "terminology_consistency"]].dropna()
        if not pts.empty:
            fig = go.Figure()
            fig.add_trace(
                go.Scattergl(
                    x=pts["semantic_preservation"],
                    y=pts["terminology_consistency"],
                    mode="markers",
                    marker=dict(size=7, color="#e08a2e", opacity=0.6),
                )
            )
            fig.update_layout(
                title="Semantic preservation vs terminology consistency",
                xaxis=dict(title="semantic preservation", range=[0, 1.02]),
                yaxis=dict(title="terminology consistency", range=[0, 1.02]),
                template="plotly_white",
                height=380,
                showlegend=False,
            )
            st.plotly_chart(fig, width="stretch")

    st.markdown("### Results table")
    st.dataframe(
        df[
            [
                "example_id",
                "overall_score",
                "semantic_preservation",
                "terminology_consistency",
                "passed",
                "error",
            ]
        ],
        width="stretch",
    )

    st.markdown("### Inspect a result")
    ex_id = st.selectbox("Example", df["example_id"].tolist())
    row = df[df["example_id"] == ex_id].iloc[0]
    st.markdown("**Response:**")
    st.markdown(f'<p class="tamil">{row["response_text"]}</p>', unsafe_allow_html=True)
    st.json(row["scores"])


def render_comparison() -> None:
    st.title("Model Comparison")
    jobs = [j for j in _load_jobs() if j["status"] == "completed"]
    if len(jobs) < 2:
        st.info("Complete at least two jobs to compare models.")
        return

    ordered = sorted(jobs, key=lambda j: j["id"])
    selected = st.multiselect(
        "Jobs to compare",
        [f"#{j['id']} {j['model_id']}" for j in ordered],
        default=[f"#{j['id']} {j['model_id']}" for j in ordered[:2]],
    )
    if not selected:
        return
    ids = [int(s.split("#")[1].split(" ")[0]) for s in selected]

    with session_scope() as session:
        from app.services.evaluation_service import compare_jobs

        report = compare_jobs(session, ids, "overall_score")

    st.markdown("### Paired comparison (identical examples)")
    st.json(report)

    st.markdown("### Per-job means")
    import pandas as pd

    rows = []
    for label, stats in report["per_job"].items():
        rows.append({"model": label, "n": stats["n"], "mean": stats["mean"]})
    st.dataframe(pd.DataFrame(rows))


def render_error_analysis() -> None:
    st.title("Error Analysis")
    jobs = _load_jobs()
    completed = [j for j in jobs if j["status"] == "completed"]
    if not completed:
        st.info("No completed jobs.")
        return
    job = completed[-1]
    _demo_banner(job["provider"])
    results = _load_results(job["id"])

    failures = [r for r in results if r["error"]]
    st.markdown(f"### {len(failures)} failed examples (of {len(results)})")
    if failures:
        from collections import Counter

        import pandas as pd

        # Use the real category name, not the example-id prefix.
        cat_by_id = {e["id"]: e["category"] for e in _load_examples()}
        cat_counts = Counter(cat_by_id.get(f["example_id"], "other") for f in failures)
        st.plotly_chart(_bar_figure(cat_counts, "Failures by category"), width="stretch")
        st.dataframe(
            pd.DataFrame(failures)[["example_id", "error", "response_text"]],
            width="stretch",
        )


def render_annotation() -> None:
    st.title("Annotation Workspace")
    st.markdown("Review examples, score dimensions independently, and track adjudication status.")

    examples = _load_examples()
    if not examples:
        st.info("No dataset loaded.")
        return

    ex_id = st.selectbox("Example", [e["id"] for e in examples])
    with session_scope() as session:
        from app.database import crud

        row = crud.get_example(session, ex_id)
        if row:
            st.markdown(f"**{row.id}** · {row.category}")
            st.markdown(f'<p class="tamil">{row.source_text}</p>', unsafe_allow_html=True)
            st.markdown("**References:**")
            for ref in row.references:
                st.markdown(f"- {ref}")

    st.markdown("### Submit review")
    reviewer = st.text_input("Reviewer name")
    semantic = st.slider("Semantic preservation", 0.0, 1.0, 0.5, 0.05)
    terminology = st.slider("Terminology consistency", 0.0, 1.0, 0.5, 0.05)
    fluency = st.slider("Fluency", 0.0, 1.0, 0.5, 0.05)
    adequacy = st.slider("Adequacy", 0.0, 1.0, 0.5, 0.05)
    cultural = st.slider("Cultural suitability", 0.0, 1.0, 0.5, 0.05)
    agrees = st.radio("Agrees with machine score?", ["yes", "no", "unsure"])
    notes = st.text_area("Notes")
    status = st.selectbox("Status", ["pending", "approved", "disputed"])

    if st.button("Submit review"):
        if not reviewer.strip():
            st.error("Reviewer name is required.")
        else:
            from app.annotation.service import submit_review
            from app.core.schemas import ReviewRecord

            with session_scope() as session:
                submit_review(
                    session,
                    ReviewRecord.model_validate(
                        {
                            "example_id": ex_id,
                            "reviewer": reviewer,
                            "semantic_score": semantic,
                            "terminology_score": terminology,
                            "fluency_score": fluency,
                            "adequacy_score": adequacy,
                            "cultural_suitability_score": cultural,
                            "agrees_with_machine": {"yes": True, "no": False, "unsure": None}[
                                agrees
                            ],
                            "status": status,
                            "notes": notes,
                        }
                    ),
                )
            st.success("Review recorded.")

    st.markdown("### Review summary")
    with session_scope() as session:
        from app.annotation.service import summarize_reviews

        summary = summarize_reviews(session, ex_id)
    st.json(
        {
            "review_count": summary.review_count,
            "avg_semantic": summary.avg_semantic,
            "avg_terminology": summary.avg_terminology,
            "disagreement": summary.disagreement,
            "status": summary.status,
            "reviewers": summary.reviewers,
        }
    )


def render_providers() -> None:
    st.title("AI Providers — Easy Connect")
    st.markdown(
        "Connect an AI model to benchmark. Keys are read from the environment "
        "(or a local, git-ignored `.env`) and are **never** stored in the database or logs."
    )

    from app.core.config import get_settings, reset_settings_cache
    from app.core.envfile import mask_secret, read_env_file, update_env_file
    from app.providers.base import ProviderAdapter
    from app.providers.presets import PRESETS
    from app.providers.registry import ProviderRegistry

    env_path = Path(".env")
    registry = ProviderRegistry()

    tab_connect, tab_local, tab_status = st.tabs(
        ["🔌 Connect a provider", "💻 Local models", "📋 Status & environment"]
    )

    with tab_connect:
        labels = [p.label for p in PRESETS]
        choice = st.selectbox("Choose a provider", labels)
        preset = next(p for p in PRESETS if p.label == choice)

        kind_badge = {"offline": "⚪ offline", "local": "🟢 local", "cloud": "🔵 cloud"}[
            preset.kind
        ]
        st.markdown(f"**{kind_badge}** · {preset.cost_note}")
        if preset.setup_hint:
            st.caption(preset.setup_hint)
        if preset.docs_url:
            st.caption(f"Docs: {preset.docs_url}")

        current = read_env_file(env_path)
        default_base = current.get(preset.env_vars.get("base_url", ""), "") or preset.base_url or ""
        default_model = current.get(preset.env_vars.get("model", ""), "") or preset.model or ""

        col1, col2 = st.columns(2)
        with col1:
            base_url = st.text_input("Base URL", value=default_base, key=f"base-{preset.id}")
        with col2:
            model = st.text_input("Model", value=default_model, key=f"model-{preset.id}")

        api_key = ""
        if preset.needs_key:
            api_key = st.text_input(
                "API key (stored locally in .env, never shown again)",
                value="",
                type="password",
                key=f"key-{preset.id}",
            )
            existing_key = current.get(preset.env_vars.get("api_key", ""), "")
            if existing_key:
                st.caption(f"An API key is already saved: {mask_secret(existing_key)}")

        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            test_clicked = st.button("🔍 Test connection", key=f"test-{preset.id}")
        with c2:
            save_clicked = st.button("💾 Save to .env", key=f"save-{preset.id}")

        if test_clicked:
            try:
                adapter: ProviderAdapter
                if preset.needs_key and api_key:
                    # Test the freshly typed credentials without saving them.
                    from app.providers.openai_compatible import OpenAICompatibleAdapter

                    if preset.provider == "anthropic":
                        from app.providers.anthropic import AnthropicAdapter

                        adapter = AnthropicAdapter(api_key=api_key, model=model, base_url=base_url)
                    else:
                        adapter = OpenAICompatibleAdapter(
                            name=preset.provider,
                            base_url=base_url,
                            api_key=api_key,
                            model=model,
                            local=preset.kind == "local",
                        )
                else:
                    adapter = registry.create(preset.provider, model or None)
                result = adapter.test_connection()
                if result.get("ok"):
                    st.success(f"Connected to {preset.provider}.")
                    models = result.get("models") or []
                    if models:
                        st.session_state[f"models-{preset.id}"] = models
                        st.caption(f"{len(models)} model(s) available — see the list below.")
                else:
                    st.error(f"Connection failed: {result.get('error', 'unknown error')}")
                st.json(result)
            except Exception as exc:  # surface a readable error, never a traceback
                st.error(f"Provider error: {exc}")

        discovered = st.session_state.get(f"models-{preset.id}")
        if discovered:
            picked = st.selectbox(
                "Available models (pick one, then Save)",
                discovered,
                key=f"pick-{preset.id}",
            )
            if st.button("Use selected model", key=f"use-{preset.id}"):
                st.session_state[f"model-{preset.id}"] = picked
                st.rerun()

        if save_clicked:
            updates: dict[str, str] = {}
            for env_var, field in preset.env_vars.items():
                if field == "base_url" and base_url:
                    updates[env_var] = base_url
                elif field == "model" and model:
                    updates[env_var] = model
                elif field == "api_key" and api_key:
                    updates[env_var] = api_key
            if not updates:
                st.warning("Nothing to save — fill in at least one field.")
            else:
                try:
                    written = update_env_file(env_path, updates)
                    reset_settings_cache()
                    st.success("Saved to .env: " + ", ".join(written) + ". Reloading settings…")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not write .env: {exc}")

    with tab_local:
        st.markdown(
            "Discover models served by a local OpenAI-compatible server "
            "(Ollama on port 11434, LM Studio on 1234)."
        )
        c1, c2 = st.columns(2)
        with c1:
            local_provider = st.selectbox("Local server", ["ollama", "lmstudio"])
        with c2:
            if st.button("🔍 Discover local models"):
                models = registry.discover_models(local_provider)
                if models:
                    st.session_state["local-models"] = models
                    st.success(f"Found {len(models)} model(s).")
                else:
                    st.warning(f"No models found on {local_provider}. Is the server running?")
        local_models = st.session_state.get("local-models")
        if local_models:
            st.dataframe(
                {"model": local_models},
                width="stretch",
            )
            st.caption(
                "Use a model by running, e.g.: "
                f"`teb eval run --provider {local_provider} --model {local_models[0]}`"
            )

    with tab_status:
        st.markdown("### Provider configuration status")
        for name, info in registry.list_configured().items():
            st.markdown(
                f"- **{name}** — {'✅ configured' if info.get('configured') else '⚪ not configured'}"
                + (f" · model `{info.get('model')}`" if info.get("model") else "")
            )
        st.markdown("### Active environment (secrets redacted)")
        st.json(get_settings().redacted_view())


def render_reports() -> None:
    st.title("Reports")
    jobs = [j for j in _load_jobs() if j["status"] == "completed"]
    if not jobs:
        st.info("No completed jobs yet.")
        return
    job = st.selectbox("Job", [f"#{j['id']} {j['name']}" for j in jobs])
    job_id = int(job.split("#")[1].split(" ")[0])
    fmt = st.selectbox("Format", ["markdown", "html", "json", "csv"])

    if st.button("Generate report"):
        with session_scope() as session:
            from app.services.reporting_service import generate_report

            content, filename = generate_report(session, job_id, fmt)
        st.success(f"Generated {filename}")
        st.download_button(
            "Download report", content, file_name=Path(filename).name, mime="text/plain"
        )
        if fmt in {"markdown", "html"}:
            st.markdown(content[:3000] + "\n\n...")


if __name__ == "__main__":
    main()
