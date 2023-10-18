# Evaluation engine

## Layered pipeline

For each example, the engine (`app/evaluation/engine.py`) computes scores in
layers. Every layer is deterministic unless an LLM judge is explicitly enabled.

1. **Constraint satisfaction** — hard, authored constraints
   (`must_contain`, `must_not_contain`, `entity_preservation`,
   `numeric_preservation`, `format`, `language`) are checked exactly.
2. **Deterministic proxy metrics** — semantic, terminology, script,
   translation, structure, and completeness signals computed without a model.
3. **Optional LLM judge** — *off by default*. When a judge callback is supplied,
   a **versioned rubric** (`app/evaluation/rubrics.py`) scores adequacy /
   fluency / cultural suitability.
4. **Human review** — annotation service (see [annotation.md](annotation.md)).

## The two primary axes

Semantic preservation and terminology consistency are **always separate scores**
— they are never merged into one number.

### Semantic preservation (0–1)

Weighted mean of four components (defaults in
`app/evaluation/semantic.py`):

| Component | Weight | Meaning |
| --- | --- | --- |
| constraint_satisfaction | 0.45 | hard constraints met |
| numeric_entity_preservation | 0.25 | numbers/entities survived |
| reference_overlap | 0.20 | token overlap with reference |
| completeness | 0.10 | content coverage |

An **empty response scores 0.0**.

### Terminology consistency (0–1)

For examples with a glossary, `app/evaluation/terminology.py` checks whether
each term was translated to an approved surface form (including inflected
variants). Unavailable (no glossary) → score is `null` with
`available=False`, never silently 0 or 1.

### Cross-example consistency

`cross_example_consistency()` groups usage by concept across many results. When
the same concept is rendered with **different** approved variants across
examples, it is flagged unstable and a `consistency_factor` (< 1.0) is
computed. On the shipped mock-provider demo run this detector flags 12 concepts
(a mock-provider artefact, not a property of real models).

## Composite score & weights

`app/evaluation/weights.py` defines `ScoreWeights`. The default weights are:

| Dimension | Default weight |
| --- | --- |
| semantic_preservation | 0.45 |
| terminology_consistency | 0.20 |
| entity_number_preservation | 0.10 |
| constraint_satisfaction | 0.15 |
| script_validity | 0.05 |
| completeness | 0.05 |

Weights are **renormalized** over the dimensions actually available for a
result, so an unavailable dimension never silently distorts the total.
The pass threshold defaults to **0.7** and lives in
`ScoreWeights.thresholds["pass"]` (equivalently `JobConfig.thresholds["pass"]`).
A result is `passed=True/False` whenever an overall score exists, and `null`
only when the score is unavailable.

## Provenance

Every dimension score carries `provenance`, one of:
`deterministic`, `reference_similarity`, `llm_judge`, or `human`. This makes it
explicit *how* each number was obtained. Deterministic dimensions do not
currently distinguish constraint checks from proxy metrics in the provenance
tag; the specific method is described in each dimension's `notes`/`evidence`.

## Rubric (LLM judge)

`app/evaluation/rubrics.py` holds `PROMPT_VERSION = "prompt-v1"` and per-category
task instructions (`TASK_INSTRUCTIONS`). The judge is only invoked when a
`judge_callback` is provided; its model and version are recorded with the job.

## Aggregation

`app/evaluation/aggregation.py` computes per-job and per-category means,
pass rates, and a **paired bootstrap** comparison between two jobs on their
common examples (`paired_difference`), reporting mean difference and a 95%
confidence interval.
