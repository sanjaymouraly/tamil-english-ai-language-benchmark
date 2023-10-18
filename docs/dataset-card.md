# Dataset card — Tamil–English Benchmark (TEB) v1.0.0

## Overview

| Field | Value |
| --- | --- |
| Name | Tamil–English AI Language Quality Benchmark (TEB) |
| Version | 1.0.0 |
| Content hash | `ca6b0c19e1fbc1b4` |
| Examples | 160 (16 categories × 10) |
| Languages | Tamil (`ta`), English (`en`), Tanglish / code-mixed (`ta+en`), romanized Tamil |
| Scripts | Tamil, Latin, mixed |
| Partitions | train 110 / dev 23 / test 27 (assigned by `sha256(example_id)`) |
| Formats | JSONL (canonical), CSV, Parquet, plus a JSON manifest |
| Data licence | CC-BY-4.0 |
| Code licence | MIT |
| Contact / maintainers | see `CONTRIBUTING.md` |

## Motivation

Most public evaluation sets for Indic languages test translation in one
direction and score it against a single reference string. TEB instead targets
the failure modes that matter in real Tamil–English products: dropped negation,
altered numbers and times, wrong honorifics/register, literal idiom translation,
code-mixing that is not parsed, and terminology that drifts across a document.
It reports **semantic preservation** and **terminology consistency** as separate
scores so a fluent-but-wrong answer cannot hide behind good surface form.

## Composition

Ten examples in each of sixteen categories:

| Category | What it probes |
| --- | --- |
| `translation_ta_to_en` | Tamil → English adequacy, negation, time, entities |
| `translation_en_to_ta` | English → Tamil naturalness and register |
| `code_mixed_understanding` | Tanglish comprehension and response |
| `romanized_transliteration` | Romanized Tamil → script + meaning |
| `register_formality` | Formal vs colloquial Tamil; honorifics |
| `instruction_following` | Length/format/language constraints |
| `customer_support` | Empathetic dialogue, entity preservation |
| `business_email` | Email structure, names, dates, amounts |
| `idiom_culture` | Idioms and cultural practices |
| `ambiguity_context` | Polysemy resolved by context |
| `technical_terminology` | Consistent domain glossaries |
| `summarization_rewriting` | Fact-preserving compression |
| `entities_numbers` | Numbers, dates, units, currency |
| `long_context_multiturn` | Multi-turn consistency |
| `language_switching` | Register/target-language adaptation |
| `safety_critical` | High-stakes quantity/instruction fidelity |

Difficulty mix: easy 56, medium 69, hard 35. Register: neutral 101, formal 35,
informal 24. Every record carries at least one critical constraint, 78 carry a
glossary, and records average 2.9 acceptable references.

## Record schema

Each record is validated against `benchmark/schemas/example.schema.json` and the
`BenchmarkExample` Pydantic model. Key fields:

- `id` — stable, e.g. `TEB-T2E-0001`
- `category`, `task_type`, `direction`, `difficulty`, `register`
- `source_text`, `source_script`, `source_language`, `target_language`
- `expected_behavior`
- `references` — **one or more** acceptable outputs (never a single "gold" string)
- `glossary` — expected term → translation pairs
- `critical_constraints` — deterministically checkable facts
- `context`, `phenomena`, `annotation_notes`
- `provenance`, `provenance_note`, `license`, `verification_status`

## Provenance and collection process

- **Synthetic / AI-generated.** Every record was authored for this benchmark.
  No copyrighted corpus was scraped or redistributed.
- Idioms and cultural practices referenced are traditional / public-domain.
- All names, order numbers, invoice numbers, and amounts are fictional.
- Build pipeline: `scripts/build_dataset.py` reads `benchmark/seed/*.json`,
  validates, checks duplicates and reference leakage, assigns partitions, and
  exports JSONL/CSV/Parquet + a manifest. The build is deterministic
  (byte-identical across runs; asserted by `tests/unit/test_reproducibility.py`).

## Verification status (honest)

| Level | Count | Meaning |
| --- | --- | --- |
| `machine_validated` | 160 | passed automated checks only |
| `agent_reviewed` | 0 | — |
| `human_reviewed` | 0 | — |
| `adjudicated` | 0 | — |

**No human native-speaker review has been performed.** Automated checks cannot
verify translation quality, idiom interpretation, or cultural nuance. Treat the
references as *plausible* rather than *authoritative* until human review is
recorded via the annotation workflow (`benchmark/guidelines/annotation-guidelines.md`).

## Known limitations

- References reflect a small number of acceptable answers, not the full space of
  valid Tamil paraphrases.
- Register labels (`formal`/`informal`/`neutral`) are author judgements.
- Deterministic semantic/terminology scores are **proxies**, not measurements of
  true meaning equivalence; see `docs/evaluation-methodology.md`.
- The set is balanced by construction (10 per category), not by real-world
  frequency.

## Ethical and privacy considerations

- No personal data, no real customer conversations, no PII.
- No demographic or political content; the `safety_critical` category covers
  dosage/instruction fidelity, not sensitive personal attributes.
- If you extend the dataset, do not add personal data or copyrighted text; record
  provenance and licence for every new record.

## How to load

```python
from pathlib import Path
from app.datasets.loader import load_examples

examples = load_examples(Path("benchmark/data/v1.0.0/examples.jsonl"))
print(len(examples), examples[0].id)
```

## Citation

See the "Citation" section of `README.md`.
