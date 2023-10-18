# Quickstart

A 5-minute path from clone to a completed offline benchmark.

## 1. Install

```bash
git clone <repo-url> && cd tamil-english-llm-evaluation
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
```

No paid API key is needed for the offline demo.

## 2. Verify the environment

```bash
teb doctor
```

This checks the database, the dataset file, and the provider registry, and
prints a redacted view of your settings.

## 3. Build / inspect the dataset

```bash
teb dataset build          # regenerate benchmark/data/v1.0.0/examples.jsonl (deterministic)
teb dataset stats          # 16 categories x 10 examples, partitions, directions
teb dataset validate benchmark/data/v1.0.0/examples.jsonl
teb dataset import benchmark/data/v1.0.0/examples.jsonl   # load into the database
```

## 4. Run an offline benchmark (mock provider, $0.00)

```bash
teb eval run --provider mock --name offline-demo
```

The runner evaluates all 160 examples and writes results to the SQLite
database (`data/teb.db`), then prints a completion summary (count, errors,
cost) plus any unstable terminology concepts it detected.

## 5. Read the scores

Semantic preservation and terminology consistency are **always reported
separately**:

```bash
teb eval report --job 1 --format markdown
teb eval compare --jobs 1,2 --dimension semantic_preservation
teb eval compare --jobs 1,2 --dimension terminology_consistency
```

`teb eval compare` requires **two or more** completed jobs and compares them on
the examples they have in common (paired bootstrap confidence interval).

## 6. Export reports

```bash
teb eval report --job 1 --format markdown
teb eval report --job 1 --format html
teb eval report --job 1 --format json
teb eval report --job 1 --format csv --out reports/results.csv
```

## 7. Explore the dashboard / API

```bash
streamlit run app/ui/app.py     # http://localhost:8501
teb serve                        # FastAPI on http://localhost:8000/docs
```

## What to look for

- **Semantic preservation** ≈ how well the meaning survived (constraints,
  numbers, entities, reference overlap, completeness).
- **Terminology consistency** ≈ whether glossary terms were translated the same
  way across examples (only computed when a glossary is present).
- A run passes an example when its overall score ≥ 0.7 (configurable).

See [evaluation.md](evaluation.md) for exactly how the composite score is built.
