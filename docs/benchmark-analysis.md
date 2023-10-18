# Benchmark analysis — TEB v1.0.0

Reproducible, evidence-based analysis of the Tamil–English Benchmark. **Every
number below was computed from stored results**, not estimated. Where a number is
a property of the *deterministic mock provider* rather than of a real model, it
is labelled as such.

- Dataset: TEB v1.0.0, content hash `ca6b0c19e1fbc1b4`, 160 examples.
- Offline baseline: provider `mock`, model `teb-mock-v1`, job 1, $0.00.
- Live run: provider `ollama`, local model, seeded sample — see
  [Live local-model run](#live-local-model-run-ollama).

---

## 1. Dataset composition

| Dimension | Distribution |
| --- | --- |
| Categories | 16 × 10 = 160 |
| Partitions | train 110 · dev 23 · test 27 |
| Difficulty | easy 56 · medium 69 · hard 35 |
| Register | neutral 101 · formal 35 · informal 24 |
| Language direction | ta→en 66 · en→ta 38 · ta→ta 26 · mixed→en 13 · roman-ta→ta+en 10 · mixed→ta 5 · en→en 1 · mixed→mixed 1 |
| Glossary present | 78 / 160 |
| Critical constraints present | 160 / 160 |
| Mean acceptable references per record | 2.92 |

### Source provenance

All 160 records are **synthetic / AI-generated**, authored for this benchmark.
No copyrighted corpus was scraped or redistributed. Idioms referenced are
traditional/public-domain expressions; all names, order numbers, invoice
numbers and amounts are fictional. Data licence: CC-BY-4.0. Verification level:
`machine_validated` for all 160 — **no human review has been performed**.

---

## 2. Metric definitions

| Metric | Range | Meaning |
| --- | --- | --- |
| Overall (weighted) | 0–1 | renormalized weighted mean of the available dimensions |
| Semantic preservation | 0–1 | deterministic proxy for meaning retention |
| Terminology consistency | 0–1 | glossary adherence (inflected variants accepted) |
| Pass | bool | `overall ≥ 0.7` |

See [evaluation-methodology.md](evaluation-methodology.md) for the full pipeline
and its limitations. The two primary axes are reported **separately** and are
never combined into a single quality figure.

---

## 3. Offline baseline — deterministic mock (`teb-mock-v1`)

| Metric | Value | n |
| --- | --- | --- |
| Overall (weighted) | **0.8993** | 160 |
| Semantic preservation | **0.9038** | 160 |
| Terminology consistency | **0.7824** | 72 |
| Pass rate (≥ 0.7) | **137 / 160** (85.6%) | 160 |
| Failures | 23 | — |
| Unavailable (`null`) overall scores | 0 | — |
| Cost | $0.0000 | — |

> ⚠️ These are the **reference behaviour of a deterministic mock**, not
> measurements of any commercial model. The mock deliberately injects
> hash-bucketed flaws so that the engine's detection logic is exercised.

### Per-category overall means (n = 10 each)

| Category | Mean | Category | Mean |
| --- | --- | --- | --- |
| code_mixed_understanding | 1.0000 | ambiguity_context | 0.9409 |
| language_switching | 0.9931 | safety_critical | 0.9046 |
| long_context_multiturn | 0.9600 | business_email | 0.8696 |
| translation_ta_to_en | 0.9503 | register_formality | 0.8646 |
| translation_en_to_ta | 0.9478 | idiom_culture | 0.8622 |
| customer_support | 0.9272 | instruction_following | 0.8349 |
| technical_terminology | 0.9162 | entities_numbers | 0.8337 |
| romanized_transliteration | 0.8105 | summarization_rewriting | 0.7727 |

### By difficulty, register and direction

| Slice | n | Overall mean |
| --- | --- | --- |
| easy | 56 | 0.9138 |
| medium | 69 | 0.8873 |
| hard | 35 | 0.8996 |
| formal | 35 | 0.9106 |
| neutral | 101 | 0.8837 |
| informal | 24 | 0.9483 |
| ta→en | 66 | 0.9158 |
| en→ta | 38 | 0.8817 |
| ta→ta | 26 | 0.8422 |
| mixed→en | 13 | 0.9976 |
| roman-ta→ta+en | 10 | 0.8105 |

Difficulty does **not** order the mock's scores monotonically (hard 0.8996 >
medium 0.8873). This is expected: the mock's flaws are assigned by hashing, not
by difficulty, so this slice is a sanity check on the harness rather than a
finding about difficulty. Real difficulty effects can only be measured with a
real model.

---

## 4. Failure analysis (mock baseline)

Error taxonomy counts (number of examples whose stored error string mentions
each kind; an example may mention several):

| Error kind | Examples |
| --- | --- |
| `omission` — required fact or constraint missing | 29 |
| `terminology_miss` — glossary term not rendered as specified | 18 |
| `numeric_error` — number/date/unit altered or dropped | 8 |
| `script_error` — wrong script for the target language | 8 |
| `transliteration_error` — romanization/Tamil-script rendering wrong | 3 |
| `empty_response` | 0 |

Representative failures (actual stored responses):

| Example | Category | Why it failed |
| --- | --- | --- |
| `TEB-T2E-0001` | translation_ta_to_en | response said "9 o'clock" where the source said 8 → `numeric_error` |
| `TEB-E2T-0005` | translation_en_to_ta | glossary term "file" not rendered as கோப்பு → `terminology_miss` |
| `TEB-ROM-0002` | romanized_transliteration | answered in the wrong language/script → `script_error` + `transliteration_error` |
| `TEB-E2T-0007` | translation_en_to_ta | dropped a required fact → `omission` |

These are the failure *types* the benchmark is designed to catch: altered
numbers, broken terminology, wrong script, and omissions.

---

## 5. Semantic vs terminology: evidence that they are distinct axes

Across the 72 mock examples that have **both** a semantic and a terminology
score, the correlation is **r = 0.485**. A moderate correlation is exactly what
should be expected from two related-but-distinct measurements; a value near 1.0
would indicate the axes are redundant. The mock's injected terminology flaws
push this apart deliberately, but the practical point holds: an answer can score
high on terminology and low on semantics (right words, wrong meaning) or the
reverse (right meaning, drifting terminology), and TEB makes both visible.

Terminology was **unavailable** (not zero) for 88 of 160 examples because those
examples define no glossary. TEB reports `null` with `available=false` rather
than scoring them 0, which is why the terminology mean is quoted with n = 72.

---

## 6. Cross-example terminology consistency

The job-level detector groups term usage across examples and flags concepts
rendered with more than one approved variant. On the mock run it flags **12
unstable concepts** (e.g. `meeting` → கூட்ட / கூட்டம், `train` → ரயி / ரயில்,
`password` → கடவுச்சொ / கடவுச்சொல்), with a `consistency_factor` of 0.871.

Most of these pairs are Tamil inflectional variants (stem vs inflected form), so
the detector is intentionally conservative: it flags *possible* drift for human
review rather than asserting an error. This is a known limitation of the
heuristic (see §9).

---

## 6b. Model comparison — worked example (synthetic)

To exercise the comparison workflow without a second real model, the repo ships a
**synthetic degraded baseline** (`examples/synthetic-degraded-responses.jsonl`,
generated by `scripts/make_degraded_baseline.py`). It takes the mock run's own
responses and applies deterministic degradations (a bumped digit, a truncation,
or dropped leading words).

`teb eval compare --jobs 1,2` then reports a **paired** comparison on the 160
identical examples:

| Model | n | Overall mean |
| --- | --- | --- |
| `teb-mock-v1` | 160 | 0.8993 |
| `synthetic-degraded-v1` | 160 | 0.7039 |
| Difference (mock − degraded) | 160 | **+0.1953** (95% CI 0.1629 – 0.2296) |

The paired bootstrap interval excludes zero, so the difference is well supported
*for this synthetic fixture*. This demonstrates the comparison machinery — it is
**not** a claim about any real model. The result is reported as
`ci_excludes_zero` rather than a "significance" flag, precisely to avoid
over-claiming.

---

## 7. Live local-model run (Ollama)

This is the only part of this document that measures a real model rather than
the deterministic mock.

### What was run

- Provider `ollama`, model served locally, seeded sample of benchmark examples
  (`--max`, seed 42), `temperature 0`, `max_tokens 2048`,
  `TEB_MAX_CONCURRENCY=1`, `TEB_REQUEST_TIMEOUT_SECONDS=300`.
- The exact command is recorded in [§10](#10-reproducing-these-findings).

### Result and caveat

The local model available in this environment is a **small (≈4B) reasoning
model**. On the full-length benchmark prompts it spends most of its output
budget on an internal reasoning trace, and with concurrency > 1 the local server
intermittently returned no usable answer. TEB now detects this and raises an
explicit error ("returned an empty answer after a reasoning trace") instead of
recording a misleadingly low score — an improvement over silently scoring empty
responses, but it also means this particular model could not produce a complete,
representative benchmark run here.

What this run **does** establish:

1. The live provider path works end-to-end against a real OpenAI-compatible
   server: connectivity check, model discovery, real generation, prompt
   construction, scoring, persistence, and reporting.
2. Local models are correctly costed at **$0.00**.
3. Reasoning models need a large `--max-tokens` budget and low concurrency on
   modest hardware — now documented in the README troubleshooting table.

What it does **not** establish: any comparative quality claim about Tamil–English
ability, for this model or any other. A meaningful live comparison requires a
capable model, a larger token budget, and ideally a paid provider — and it should
be published with a model card (`docs/model-card-template.md`) recording the
exact identifiers and settings.

> **Honesty note.** No live result is presented here as measured model quality,
> because the run was not representative. This is recorded as a limitation, not
> hidden.

Full analysis, failure taxonomy and limitations:
[benchmark-analysis.md](benchmark-analysis.md).

---

## 8. Uncertainty and reviewer agreement

- Per-category means are descriptive; with n = 10 per category they carry wide
  uncertainty and should not be over-interpreted.
- `teb eval compare` performs a **paired** bootstrap comparison on the
  intersection of examples evaluated by two jobs and reports a 95% confidence
  interval. A confidence interval containing zero does not support a claim that
  one model is better.
- **No human inter-annotator agreement exists yet**, because no human review has
  been performed. Reviewer disagreement tracking and adjudication are
  implemented (`docs/annotation.md`) but the dataset has no annotations.

---

## 9. Limitations and potential biases

1. **No human verification.** References are plausible, not authoritative.
2. **Deterministic proxies.** Surface matching under-detects correct Tamil
   inflections and penalises valid word-order variation. Numbers should be read
   as *evidence*, not proof of meaning equivalence.
3. **Mock artefacts.** The baseline's failures are injected by hashing; they
   demonstrate detection capability, not model behaviour.
4. **Terminology denominator.** Terminology means exclude 88/160 examples with no
   glossary; the mean is therefore over a self-selected subset.
5. **Balance by construction.** 10 per category, not real-world frequency.
6. **Register labels** are author judgements, not annotated ground truth.
7. **Cross-example flags** conflate inflection with genuine inconsistency.
8. **Single real run, unrepresentative.** See §7.
9. **No judge run.** The LLM-judge layer is implemented but not exercised
   against a real judge model, so adequacy/naturalness/cultural dimensions are
   absent from every result here.

---

## 10. Reproducing these findings

```bash
pip install -e ".[dev]"
teb dataset build                                    # deterministic; hash ca6b0c19e1fbc1b4
teb dataset import benchmark/data/v1.0.0/examples.jsonl
teb eval run --provider mock --name offline-demo      # job 1, $0.00
teb eval report --job 1 --format markdown             # reports/demo_report.markdown
teb eval report --job 1 --format html

# Live local run (optional; needs Ollama)
ollama pull <model>
teb providers discover ollama
teb eval run --provider ollama --model <model> --max 8 --max-tokens 2048 \
             --name live-local
```

Aggregate statistics in this document can be recomputed directly from the
database with `teb eval report` or from `reports/demo_report.json`.

---

## 11. Recommended areas for future work

1. **Human native-speaker review** of a stratified sample, with reported
   inter-annotator agreement, to calibrate the deterministic proxies.
2. **A real, capable model comparison** on the held-out test partition, with
   model cards and paired bootstrap intervals.
3. **Judge calibration**: run the LLM judge and compare it against human scores.
4. **Morphology-aware terminology matching** to reduce inflection false
   positives in the cross-example detector.
5. **Dialect and register metadata** (e.g. Sri Lankan Tamil, Chennai colloquial)
   as first-class fields, with coverage.
6. **Optional local multilingual embeddings** for reference-free similarity, used
   as an additional (clearly labelled) signal.
7. **Regression tracking**: store benchmark snapshots over time to detect model
   regressions between releases.
