# Dataset

## Overview

The shipped dataset (`benchmark/data/v1.0.0/examples.jsonl`) contains **160
original examples** across **16 categories**, with deterministic train/dev/test
partitions.

| Property | Value |
| --- | --- |
| Examples | 160 |
| Categories | 16 (10 examples each) |
| Partitions | train 110 / dev 23 / test 27 |
| Content hash | `ca6b0c19e1fbc1b4` |
| Validation errors | 0 |
| Origin | Synthetic / AI-generated (labelled honestly) |

## Categories

| Code | Category | Direction focus |
| --- | --- | --- |
| T2E | Tamil→English translation | ta→en |
| E2T | English→Tamil translation | en→ta |
| CMX | Code-mixed handling | mixed |
| ROM | Romanized Tamil transliteration | roman-ta→ta+en |
| REG | Register adaptation | mixed registers |
| INS | Instruction following | various |
| SUP | Summarization | various |
| BEM | Backend entity matching | entity-heavy |
| IDM | Idiom / cultural expression | ta↔en |
| AMB | Ambiguity resolution | various |
| TER | Terminology consistency | glossary-heavy |
| ENT | Named entity preservation | entity-heavy |
| LNG | Language detection | various |
| SUM | Structural / numeric fidelity | numeric |
| SWI | Script / transliteration | script |
| SAF | Safety / appropriateness | various |

## Example schema

Each record conforms to `benchmark/schemas/example.schema.json` and the
`BenchmarkExample` Pydantic model:

```json
{
  "id": "TEB-T2E-0001",
  "category": "tamil_to_english",
  "source_language": "ta",
  "target_language": "en",
  "direction": "ta->en",
  "source_text": "…",
  "reference": "…",
  "glossary": [{"term": "…", "translation": "…", "language": "en"}],
  "critical_constraints": [{"kind": "must_contain", "value": "…"}],
  "register_level": "formal",
  "difficulty": "medium",
  "requires_list": false,
  "entity_types": ["PERSON", "ORG"]
}
```

- **`id`** matches `TEB-<CAT>-<nnnn>` and is stable across exports.
- **`content_hash`** = first 16 hex chars of the SHA-256 of the canonical
  record; used for dedup and change detection.
- **`register_level`** is serialized under the alias `register`.

## Validation rules

`app/datasets/validator.py` enforces: required fields, allowed category /
language / direction / register / difficulty values, ID pattern, non-empty
source text, ≥1 reference, glossary term/translation pairing, and constraint
well-formedness. Duplicate detection (`check_duplicates`) flags identical
normalized source text and near-duplicates (character 3-gram Jaccard > 0.95).

## Partitions

`app/datasets/partitions.py` assigns splits by `sha256(example_id)`, so a given
example is always in the same partition regardless of file order:
70% train / 15% dev / 15% test (rounded deterministically).

## Versioning & registry

Every import is stored with a **dataset version** (default `1.0.0`) and its
**content hash**, so results can always be traced to the exact dataset they were
produced on. `data/registry/index.json` records the loaded datasets.

```bash
teb dataset import benchmark/data/v1.0.0/examples.jsonl   # registers a version
teb dataset export reports/dataset_export.jsonl            # lossless round-trip
```

## Rebuilding from seed

The 16 seed files in `benchmark/seed/01…16_*.json` are the human-authored
source of truth. `scripts/build_dataset.py` normalizes them, validates, dedups,
assigns partitions, and writes `benchmark/data/v1.0.0/`.

```bash
python3 -m scripts.build_dataset
```
