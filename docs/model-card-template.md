# Model card template

Copy this file to `docs/model-cards/<provider>-<model>.md` when you publish
results for a specific model. Fill in only what you actually measured — leave
fields blank rather than guessing.

---

## Model

| Field | Value |
| --- | --- |
| Display name | |
| Provider | |
| Exact model identifier (as reported by the provider) | |
| Access route | e.g. OpenAI API / OpenRouter / Ollama (local) |
| Version / snapshot date | |
| Context window | |
| Decoding settings used | temperature, max_tokens |
| Prompt version | `prompt-v1` |
| Rubric version | `rubric-v1` |
| Judge used? | no / yes (model id) |

## Evaluation setup

| Field | Value |
| --- | --- |
| Dataset version | TEB v1.0.0 |
| Dataset content hash | `ca6b0c19e1fbc1b4` |
| Partition / subset | |
| Examples evaluated (n) | |
| Errors / unavailable responses | |
| Job id(s) | |
| Code revision | |

## Results

| Metric | Value | n |
| --- | --- | --- |
| Overall (weighted) | | |
| Semantic preservation | | |
| Terminology consistency | | |
| Constraint satisfaction | | |
| Entity/number preservation | | |
| Script validity | | |
| Pass rate (≥ 0.7) | | |
| Estimated / actual cost (USD) | | |
| Median latency (ms) | | |

Per-category overall means:

| Category | n | Overall | Semantic | Terminology |
| --- | --- | --- | --- | --- |
| | | | | |

## Failure analysis

Summarise the dominant failure types (see the error taxonomy:
`empty_response`, `omission`, `numeric_error`, `terminology_miss`,
`terminology_inconsistent`, `script_error`, `negation_error`,
`structural_error`, `hallucination`, `transliteration_error`) with two or three
concrete examples (example id + response + why it failed).

## Provenance of these results

- [ ] Deterministic metrics only (no judge, no human review)
- [ ] LLM judge used (rubric version recorded)
- [ ] Human review performed (reviewers named in the annotation records)
- [ ] Results reproduced independently

## Limitations

- Were any provider errors or timeouts excluded? If so, say so and how many.
- Was the sample a full partition or a seeded subset?
- Any known provider quirks (e.g. reasoning models returning empty content when
  the token budget is exhausted)?

## Cost and reproducibility notes

Record the exact command(s) used:

```bash
teb eval run --provider <p> --model <m> --config configs/<file>.json --name <name>
teb eval report --job <id> --format markdown --out reports/<file>.md
```

## Ethical considerations

Note any deployment caveats for Tamil/English use (e.g. register handling,
safety-critical quantity fidelity, dialect coverage).
