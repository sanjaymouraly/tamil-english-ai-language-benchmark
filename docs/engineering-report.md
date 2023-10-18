# Engineering report — Tamil–English AI Language Quality Benchmark (TEB)

**Version:** 0.1.0 · **Date:** 2026-10-18

## 1. What was built

A production-oriented, open-source benchmark platform for measuring
Tamil–English language quality in AI systems. It delivers:

- an **original 160-example dataset** across 16 categories with deterministic
  train/dev/test partitions and a **reproducible build**;
- a **layered evaluation engine** that reports **semantic preservation** and
  **terminology consistency** as separate, always-distinct scores;
- **cost-aware provider adapters** (OpenAI-compatible, Anthropic, OpenRouter,
  Ollama, LM Studio, custom, deterministic mock, offline replay) with an
  **easy-connect** setup UI, credential checks before use, bounded retries, and
  a hash-keyed response cache;
- three front-ends: **Streamlit dashboard**, **FastAPI service**, **Typer CLI**;
- **reproducible reports** (Markdown / HTML / JSON / CSV) stamped with
  dataset / prompt / rubric / code versions and a content hash;
- a **human annotation & adjudication** workflow with honest
  verification-level labels;
- **175 tests**, docs, CI, and Docker packaging.

## 2. Dataset

| Property | Value |
| --- | --- |
| Examples | 160 (16 categories × 10) |
| Partitions | train 110 / dev 23 / test 27 |
| Content hash | `ca6b0c19e1fbc1b4` |
| Validation errors | 0 |
| Origin | Synthetic / AI-generated (labelled honestly) |
| Verification level | `machine_validated` (no human review yet) |

Categories: translation (ta→en, en→ta), code-mixed understanding, romanized
transliteration, register/formality, instruction following, customer support,
business email, idiom/culture, ambiguity, technical terminology, summarization,
entities/numbers, long context, language switching, safety-critical.

The dataset is rebuilt from 16 human-authored seed files (`benchmark/seed/`) via
`teb dataset build`, validated against a JSON Schema, deduplicated, partitioned
by SHA-256 of the example ID, and versioned in a registry.

**Reproducibility.** The build is deterministic: it pins a fixed release
timestamp, and the content hash covers only substantive fields (ingestion
metadata is excluded), so repeated builds are byte-identical and the hash is
stable across machines. Asserted by `tests/unit/test_reproducibility.py`.

## 3. Evaluation methodology

Layered pipeline per example:

1. **Deterministic constraints** — `must_contain`, `must_not_contain`, regex,
   entity/numeric preservation.
2. **Deterministic proxy metrics** — semantic (constraint satisfaction,
   numeric/entity preservation, reference overlap, completeness),
   terminology (glossary adherence + inflected variants), script fidelity,
   transliteration, structure, completeness.
3. **Optional LLM judge** — off by default; versioned rubric
   (`prompt-v1`, `rubric-v1`).
4. **Human review / adjudication** — separate verification levels.

**Composite score** = renormalized weighted mean over available dimensions
(semantic 0.45, terminology 0.20, entity/number 0.10, constraint 0.15, script
0.05, completeness 0.05). Pass threshold 0.7. A result is `passed=True/False`
whenever an overall score exists, and `null` only when unavailable.

Every dimension score carries a **provenance** tag (`deterministic`,
`reference_similarity`, `llm_judge`, `human`). Unsupported metrics are `null`
with `available=False` — never silently scored.

## 4. Results

### Deterministic mock provider (`teb-mock-v1`, $0.00) — job 1, all 160 examples

| Metric | Value |
| --- | --- |
| Completed | 160 / 160 (0 errors) |
| Overall mean | **0.8993** |
| Semantic preservation mean | **0.9038** (n = 160) |
| Terminology consistency mean | **0.7824** (n = 72) |
| Pass rate (≥ 0.7) | 137 / 160 (23 fail, 0 unavailable) |
| Estimated/actual cost | $0.0000 |

Per-category overall means are in [benchmark-analysis.md](benchmark-analysis.md).

The mock deliberately injects hash-bucketed flaws, so 38 examples carry at least
one error flag and the engine flags **12 unstable terminology concepts** —
confirming the cross-example consistency detector works.

> These are **reference-behaviour numbers for the deterministic mock**, not
> claims about any commercial model.

### Live local model (Ollama)

A real end-to-end run against a locally served Ollama model was executed. The
measured numbers, failure taxonomy and caveats are recorded in
[benchmark-analysis.md](benchmark-analysis.md). No commercial API was called
(no credentials were available).

## 5. Verification status

**Verified:**
- 175 tests pass (`pytest`): unit (schemas, validator, semantic, terminology,
  constraints, metrics, providers, presets, env-file, cost, weights,
  aggregation, config, security), integration (database CRUD, HTTP API, CLI,
  evaluation engine, import/export round-trip), and end-to-end offline
  benchmark runs.
- `ruff check`, `ruff format --check` and `mypy app` are clean (0 errors).
- Full offline benchmark completes 160/160 with 0 errors, $0.00, and a correct
  pass/fail signal.
- FastAPI verified via TestClient — all routes return documented codes,
  unknown provider → 400, missing example → 404.
- Streamlit dashboard boots, serves HTTP 200, and all 9 pages render; real
  screenshots committed in `docs/screenshots/`.
- Dataset build is reproducible (byte-identical output, stable hash).
- Dataset import/export round-trip is lossless, including `register`.
- Reports carry dataset/prompt/rubric/code versions + content hash.
- Docker image builds; container entrypoint smoke-tested (`cli doctor`).

**Not verified / honest limitations:**
- No human annotation yet — all records are `machine_validated`.
- Mock scores are not commercial-model scores.
- Commercial provider paths are implemented and credential-checked but were not
  exercised against real endpoints here.
- The LLM judge layer is unit-tested with a stub but not run against a real
  judge model.
- Linux/macOS execution was not performed locally (CI is configured for both).
- Deterministic proxies are approximations; Tamil morphological inflection
  matching is heuristic.

See [verification.md](verification.md).

## 6. Defects found and fixed during this build

The first implementation had several real defects, all fixed with regression
tests. Full list in [CHANGELOG.md](../CHANGELOG.md).

| Defect | Impact | Fix |
| --- | --- | --- |
| Content hash included `created_at` | Hash changed every build; "deterministic build" claim was false | Hash substantive fields only; pin the release timestamp |
| `register` lost on export/import | `formal`/`informal` silently became `neutral` on every round-trip | Enable population by field name; round-trip tests |
| `passed` was `null` for failures | `(... >= t) or None` collapsed `False` to `None` | `None if overall is None else overall >= t` |
| `OPENAI_API_KEY` ignored | `.env.example` documented names the app never read | Accept bare and `TEB_`-prefixed names |
| `teb dataset build` failed | `import scripts...` not importable from the console script / container | Moved the pipeline into `app.datasets.build` |
| Response cache never used | README claimed a cache that was dead code | Wired the cache into live adapters; fixed key to include `meta` |
| Windows Tamil output crashed the CLI | `UnicodeEncodeError` on cp1252 | Reconfigure stdout/stderr to UTF-8 |
| Instruction-following was fabricated | Hardcoded 1.0/0.2 scores | Derived from checkable requirements; `null` when none |
| Judge called `generate(**kwargs)` | Would `TypeError` on first real use | Build a `GenerationRequest` |
| `TEB_REQUEST_TIMEOUT_SECONDS` unused | Timeouts could not be configured | Wired into every adapter |
| Anthropic errors unredacted | API key could leak into an error message | Redact like the OpenAI adapter |
| Cost matched unknown short ids | `"gpt"` inherited `gpt-4o-mini` pricing | Longest forward prefix match only |
| Streamlit could not import `app` | Dashboard failed to start from a fresh clone | Robust `sys.path` bootstrap |
| Results persisted in completion order | Non-deterministic storage order | Sort by dataset order |
| `DimensionScore.notes` dropped | Silently ignored by Pydantic | Added the field |

## 7. Architecture

```
Entry points:  Streamlit UI · FastAPI · Typer CLI (teb)
                    │
              Services (evaluation, reporting)
                    │
   ┌────────────────┴─────────────────┐
Evaluation engine                 Reporting (MD/HTML/JSON/CSV)
constraints → proxies → judge
                    │
   ┌────────────────┴─────────────────┐
Providers (openai, anthropic,      Database (SQLite + SQLAlchemy
openrouter, ollama, lmstudio,       + Alembic)
custom, mock, offline;
retry/cost/cache)
                    │
           Dataset layer (loader, build, validator,
           partitions, registry)
```

## 8. How to reproduce

```bash
pip install -e ".[dev]"
teb doctor
teb dataset build && teb dataset stats
teb dataset import benchmark/data/v1.0.0/examples.jsonl
teb eval run --provider mock --name demo      # $0.00, 160/160
teb eval report --job 1 --format html
pytest                                         # 175 tests
ruff check app scripts tests && ruff format --check app scripts tests
mypy app
python scripts/screenshot.py                   # re-capture screenshots
docker build -t teb:local . && docker run --rm teb:local cli doctor
```

## 9. Deliverables

- Source: `app/`, `scripts/`, `benchmark/`, `migrations/`, `configs/`, `examples/`
- Tests: `tests/` (175)
- Docs: `README.md`, `docs/` (quickstart, architecture, dataset, dataset card,
  evaluation, evaluation methodology, benchmark analysis, providers, API, CLI,
  reports, annotation, verification, model-card template, this report)
- Reports: `reports/` (demo MD/HTML/JSON/CSV)
- Screenshots: `docs/screenshots/` (real app captures)
- Ops: `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `Makefile`
