# Contributing to the Tamil–English AI Language Quality Benchmark (TEB)

Thanks for helping improve bilingual AI evaluation. This project takes
**honesty about verification** seriously: contributions that add data or
results must be traceable and must not overstate how they were validated.

## Ways to contribute

- **Dataset examples** — new Tamil/English/Tanglish benchmark items.
- **Human review** — native-speaker annotations (see the annotation workflow).
- **Evaluation metrics** — better deterministic checks or judge rubrics.
- **Providers** — new AI backends behind the common adapter interface.
- **Docs, UI, tests, bug fixes.**

## Development setup

```bash
git clone <repo-url> && cd tamil-english-llm-evaluation
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
teb doctor
pytest -q
```

Useful commands (or `make help`):

```bash
ruff check app scripts tests        # lint
ruff format app scripts tests       # format
mypy app                            # static types
pytest -q                           # tests
teb dataset build                   # rebuild dataset from seeds
teb eval run --provider mock        # offline benchmark, $0.00
```

## Adding dataset examples

1. Add records to the relevant file in `benchmark/seed/` (one JSON array per
   category). Every record must satisfy `benchmark/schemas/example.schema.json`
   and the `BenchmarkExample` Pydantic model.
2. Required fields include `id` (`TEB-<CAT>-NNNN`), `category`, `direction`,
   `source_text`, `source_script`, `expected_behavior`, `references`,
   `difficulty`, and honest `provenance`.
3. Provide **multiple acceptable references** where more than one translation is
   valid. Do not assume a single reference string is the only correct answer.
4. Add `glossary` entries when terminology consistency matters, and
   `critical_constraints` for facts that must survive (numbers, negation,
   entities).
5. Rebuild and validate:

   ```bash
   teb dataset build
   teb dataset validate benchmark/data/v1.0.0/examples.jsonl
   ```

6. **Provenance rules**
   - Label synthetic/AI-generated records as `synthetic`.
   - Do not redistribute copyrighted corpora without a compatible licence.
   - Do not claim human verification you did not perform. Set
     `verification_status` honestly (`machine_validated` is the default).

## Adding a provider

1. Implement `ProviderAdapter` (`app/providers/base.py`): `generate`,
   `test_connection`, `estimate_cost`.
2. Register it in `app/providers/registry.py` and, if it is a user-facing
   vendor, add a preset in `app/providers/presets.py`.
3. Never log or persist API keys. Add a mocked test in `tests/unit/test_providers.py`.

## Pull requests

- Keep changes focused; one logical change per PR.
- Run `ruff check`, `ruff format --check`, `mypy app`, and `pytest -q` locally.
- Add or update tests for behaviour changes.
- Update documentation (`docs/`, `README.md`) when you change behaviour.
- Do **not** commit `.env`, API keys, private datasets, or large model files.

## Code of conduct

Be respectful and constructive. Assume good faith. Report unacceptable
behaviour to the maintainers.
