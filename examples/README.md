# Examples

Small, runnable inputs for the offline workflows. Nothing here calls a paid API.

## `imported-responses.example.jsonl`

Pre-collected model responses for ten benchmark examples, in the JSONL shape the
**offline provider** and `teb eval responses-import` expect:

```json
{"example_id": "TEB-T2E-0001", "response_text": "I am going to school at 8 o'clock today morning."}
```

Evaluate them without any network access:

```bash
teb dataset build
teb dataset import benchmark/data/v1.0.0/examples.jsonl
teb eval run --provider offline --offline-file examples/imported-responses.example.jsonl \
             --name offline-import-demo
teb eval report --job <id> --format markdown
```

Only the ten ids present in the file are evaluated; the offline provider raises a
clear error for any example without an imported response.

## Importing your own responses

Any JSONL with `example_id` (or `id`) and `response_text` (or `response`/`text`)
works:

```bash
teb eval responses-import my_model_outputs.jsonl --model-id my-model-v1
```

You can also generate a file by running a provider once and exporting the
responses, then re-evaluating them deterministically later.

## `synthetic-degraded-responses.jsonl`

A **synthetic fixture** for demonstrating the Model Comparison workflow without a
second real model. It contains all 160 benchmark responses with deterministic,
deliberately-introduced degradations (a bumped digit, a truncation, or dropped
leading words), so the comparison produces a genuinely lower score.

Regenerate it with:

```bash
teb dataset build && teb dataset import benchmark/data/v1.0.0/examples.jsonl
teb eval run --provider mock --name offline-demo                       # job 1
python scripts/make_degraded_baseline.py --job 1 \
       --out examples/synthetic-degraded-responses.jsonl
teb eval run --provider offline --model synthetic-degraded-v1 \
       --offline-file examples/synthetic-degraded-responses.jsonl \
       --name synthetic-degraded-baseline                              # job 2
teb eval compare --jobs 1,2
```

> ⚠️ This is a **synthetic, deliberately weaker** baseline created to exercise
> the comparison UI and the paired-bootstrap statistics. It is **not** a real
> model and must never be presented as measured model performance.
