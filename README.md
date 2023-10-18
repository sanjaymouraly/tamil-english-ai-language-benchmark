# Tamil–English AI Language Quality Benchmark

A benchmark for measuring Tamil–English language quality across translation, reasoning, and fluency tasks.

## Features

- 160 original Tamil–English examples across 16 categories with deterministic train/dev/test splits.
- Separate semantic-preservation and terminology-consistency scores.
- Layered evaluation: deterministic constraints, proxy metrics, an optional LLM judge, and human review.
- Deterministic dataset builds with stable content hashes.
- Reports record the dataset hash, prompt and rubric versions, decoding settings, and cost.
- A fully offline demo needs no paid API.

## Stack

Python, FastAPI, Uvicorn, SQLAlchemy, Streamlit, Typer, Pydantic, pandas, NumPy, SciPy

## Clone

```bash
git clone https://github.com/sanjaymouraly/tamil-english-ai-language-benchmark.git
cd tamil-english-ai-language-benchmark
```

## Setup

```bash
# The project ships a Docker Compose setup.
docker compose up --build
```

See `docs/` or the compose file for environment variables and ports.

## Run

```bash
docker compose up --build
```

## Tests

```bash
pytest -q
```

## Notes

- Sample data, when included, is synthetic.

## License

MIT © 2023 [Sanjay Mouraly](https://github.com/sanjaymouraly)
