# Architecture

```
                 ┌────────────────────────────────────────────┐
                 │  Entry points                              │
                 │  Streamlit UI · FastAPI · Typer CLI        │
                 └───────────────┬────────────────────────────┘
                                 │
                 ┌───────────────▼────────────────────────────┐
                 │  Services                                  │
                 │  evaluation_service · reporting_service    │
                 └───────┬───────────────────────┬────────────┘
                         │                       │
        ┌────────────────▼─────────┐   ┌─────────▼──────────────┐
        │  Evaluation engine       │   │  Reporting             │
        │  constraints → proxies   │   │  markdown/html/json/csv│
        │  → (opt. LLM judge)      │   └────────────────────────┘
        │  → human review          │
        └────────────────┬─────────┘
                         │
        ┌────────────────▼─────────┐   ┌────────────────────────┐
        │  Providers               │   │  Database            │
        │  openai · anthropic      │   │  SQLite + SQLAlchemy │
        │  mock · offline          │   │  + Alembic           │
        │  + retry/cost/cache      │   └────────────────────────┘
        └──────────────────────────┘
                         │
        ┌────────────────▼─────────┐
        │  Dataset layer           │
        │  loader · validator      │
        │  partitions · registry   │
        └──────────────────────────┘
```

## Layer responsibilities

- **`app/core`** — settings (pydantic-settings, `TEB_` prefix), Pydantic
  schemas, security (filename / data-file validation, PII detection, script
  detection), redacting logging, typed errors.
- **`app/datasets`** — multi-format loading/export, validation, dedup,
  deterministic partitions, dataset registry/versioning.
- **`app/evaluation`** — the layered engine, deterministic metrics, terminology
  handling, rubric, weights, aggregation, the orchestrating runner.
- **`app/providers`** — uniform `ProviderAdapter` interface, httpx-based adapters,
  deterministic mock and offline replay, credential checks, retries, cost, cache.
- **`app/database`** — SQLAlchemy models, session/engine factory, CRUD.
- **`app/services`** — use-case orchestration shared by UI/API/CLI.
- **`app/annotation`** — human review and adjudication.
- **`app/reporting`** — multi-format report generation (Markdown, HTML with
  embedded interactive Plotly charts, JSON, CSV).
- **`app/api`, `app/cli`, `app/ui`** — the three front-ends.

## Key invariants

1. Semantic preservation and terminology consistency are **always separate**.
2. Unsupported metrics are `null` + `available=False`, never silently scored.
3. Live providers are used only with credentials present.
4. References reach mock/offline providers via `request.meta` only.
5. Every result and report is stamped with dataset / prompt / rubric / code
   versions and the dataset content hash.

## Data flow (one job)

`create_job` → runner iterates examples → for each, provider generates a
response → engine scores it (constraints → proxies → optional judge) → result
persisted with per-dimension scores and provenance → aggregation computes
job/category means and cross-example consistency → reports exported.
