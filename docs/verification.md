# Verification status

This document states, plainly, what has and has not been verified. It is updated
honestly whenever the state changes.

## What is verified

- **Dataset integrity.** 160 examples, 16 categories × 10, deterministic
  partitions (train 110 / dev 23 / test 27), zero validation errors, content
  hash `ca6b0c19e1fbc1b4`. Import/export round-trip is lossless — including the
  `register` field, which an earlier build silently dropped (regression test:
  `tests/integration/test_roundtrip.py`).
- **Dataset build reproducibility.** `teb dataset build` is deterministic:
  repeated builds produce byte-identical JSONL/CSV/Parquet and a stable content
  hash. The content hash excludes ingestion metadata (`created_at`). Regression
  test: `tests/unit/test_reproducibility.py`.
- **Test suite.** 175 tests pass (`pytest`): unit tests for schemas, validator,
  semantic, terminology, constraints, metrics, providers, presets, env-file
  handling, cost, weights, aggregation, config and security; integration tests
  for database CRUD, the HTTP API, the CLI, the evaluation engine and
  import/export round-trips; end-to-end offline benchmark tests.
- **Static analysis.** `ruff check`, `ruff format --check` and `mypy app` all
  pass cleanly (0 errors).
- **Offline benchmark.** A full 160/160 run with the deterministic mock provider
  completes with 0 errors and $0.00 cost, producing separate semantic (0.9038)
  and terminology (0.7824) means and a correct pass/fail signal
  (137 pass / 23 fail / 0 unavailable).
- **Live local-model run.** A real run against a locally served Ollama model
  was executed end-to-end; see `docs/benchmark-analysis.md` for the actual
  numbers and the honest caveats.
- **API surface.** Every route returns the documented status codes (verified via
  FastAPI TestClient), including a clean `400` for an unknown provider and `404`
  for a missing example.
- **Dashboard.** The Streamlit app boots, serves HTTP 200, and every page
  renders; real screenshots are committed in `docs/screenshots/`.
- **Docker.** The image builds successfully and the container's entrypoint
  (dataset build + import + migrations + `teb doctor`) was smoke-tested.
- **Configuration.** Both bare (`OPENAI_API_KEY`) and `TEB_`-prefixed
  environment variables are honoured, with prefixed taking precedence.

## What is NOT verified / honest limitations

- **No human annotation yet.** All shipped records are synthetic /
  AI-generated and only `machine_validated`. No `human_reviewed` or
  `adjudicated` labels exist in the shipped dataset.
- **Mock scores are not model scores.** The demo numbers come from a
  deterministic mock that injects hash-bucketed flaws. They are reference
  behaviour, not claims about any commercial model.
- **No commercial API was exercised.** No OpenAI/Anthropic/OpenRouter
  credentials were provided, so those adapters are implemented, credential-
  checked, and unit-tested with mocks, but were not run against real endpoints
  here.
- **The LLM judge layer** is implemented and unit-tested with a stub provider,
  but has not been run against a real judge model.
- **Linux/macOS execution** was not performed in this environment; the commands
  are documented and covered by the GitHub Actions matrix, but that is not the
  same as a verified local run.
- **Deterministic proxy metrics** (token overlap, entity/number preservation,
  script detection) are approximations. They are labelled `deterministic` in
  provenance and are not a substitute for human or LLM-judged evaluation.
- **Tamil morphological inflection** in terminology matching is heuristic; rare
  inflected forms may be missed. Cross-example consistency flags are advisory.
- **Reasoning models** may return an empty answer when the token budget is
  exhausted by their thinking trace; TEB raises a clear error rather than
  recording a misleadingly low score, but this still limits automatic runs.

## Reproducing every claim

```bash
pip install -e ".[dev]"
pytest                                   # 175 tests
ruff check app scripts tests && ruff format --check app scripts tests
mypy app
teb dataset build                        # deterministic; stable hash
teb dataset stats                        # 160 / 16 categories / partitions
teb eval run --provider mock --name offline-demo
teb eval report --job 1 --format html    # reproducible report
python scripts/screenshot.py             # re-capture docs/screenshots
docker build -t teb:local . && docker run --rm teb:local cli doctor
```
