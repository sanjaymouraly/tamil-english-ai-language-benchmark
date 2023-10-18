# Evaluation methodology

This document describes *how* TEB produces scores, what those scores do and do
not mean, and how to reproduce an evaluation. It is the reference for anyone
interpreting a TEB report.

## Principles

1. **Separate the axes.** Semantic preservation and terminology consistency are
   always reported as separate numbers. They are never merged into a single
   "quality" figure that hides a semantic error behind good surface form.
2. **Layer the evidence.** Deterministic checks first, then reference-based
   similarity, then (optionally) an LLM judge, then human review. Each layer is
   labelled with its provenance.
3. **Never invent a score.** If a dimension cannot be measured for an example it
   is reported as `null` with `available=false`, not as 0 or 1.
4. **Distinguish measurement from judgement.** Deterministic proxies are labelled
   as proxies. Judge output is labelled `llm_judge`. Human review is separate.
5. **Reproducibility over novelty.** Everything needed to re-run and audit a
   result is stored with the job (dataset hash, prompt/rubric version, decoding
   settings, code revision, cost).

## Pipeline per example

```
source text ──► prompt (versioned) ──► provider ──► response
                                                       │
      ┌────────────────────────────────────────────────┴───────────────┐
      │ Layer 1  deterministic checks                                  │
      │   • critical constraints (must_contain / must_not_contain /     │
      │     regex / numeric_preservation / entity_preservation)         │
      │   • numeric, date, time, unit, currency preservation            │
      │   • glossary adherence (+ inflected variants)                   │
      │   • script validity, transliteration, structure, completeness   │
      ├────────────────────────────────────────────────────────────────┤
      │ Layer 2  reference-based similarity (informational component)   │
      ├────────────────────────────────────────────────────────────────┤
      │ Layer 3  optional LLM judge (off by default, versioned rubric)  │
      ├────────────────────────────────────────────────────────────────┤
      │ Layer 4  human review / adjudication (separate records)         │
      └────────────────────────────────────────────────────────────────┘
```

## Dimensions

| Dimension | Layer | Notes |
| --- | --- | --- |
| `constraint_satisfaction` | deterministic | fraction of authored constraints met |
| `entity_number_preservation` | deterministic | numbers/dates/times/units from source survive |
| `semantic_preservation` | deterministic proxy | weighted mean of four sub-signals (below) |
| `terminology_consistency` | deterministic | glossary adherence; `null` when no glossary |
| `script_validity` | deterministic | correct script for the target language |
| `completeness` | deterministic | sensible length band vs references |
| `fluency` | deterministic heuristic | mechanical defects only (repetition, unbalanced brackets, mojibake) |
| `transliteration_accuracy` | deterministic | romanized-Tamil examples only |
| `instruction_following` | deterministic | structural requirements only; `null` if none defined |
| `adequacy`, `naturalness`, `cultural_suitability`, `code_mix_appropriateness`, `hallucination` | LLM judge | only when a judge is enabled |

### Semantic preservation sub-components

| Component | Default weight |
| --- | --- |
| constraint_satisfaction | 0.45 |
| numeric_entity_preservation | 0.25 |
| reference_overlap | 0.20 |
| completeness | 0.10 |

An empty response scores 0.0. Reference overlap is deliberately the smallest
component: lexical overlap is *not* semantic equivalence, and correct Tamil
answers frequently differ from every reference string.

### Composite score

The composite is a weighted mean over the dimensions that produced a score:

| Dimension | Default weight |
| --- | --- |
| semantic_preservation | 0.45 |
| terminology_consistency | 0.20 |
| entity_number_preservation | 0.10 |
| constraint_satisfaction | 0.15 |
| script_validity | 0.05 |
| completeness | 0.05 |

Weights are renormalized over available dimensions. Weights are configurable
(`configs/*.json`), but **semantic and terminology scores remain separate
regardless of the weighting**. Pass threshold defaults to 0.7.

## Provenance tags

| Tag | Meaning |
| --- | --- |
| `deterministic` | computed without a model, reproducible bit-for-bit |
| `reference_similarity` | computed against reference strings |
| `llm_judge` | produced by a language model under a versioned rubric |
| `human` | entered by a named human reviewer |

An LLM-judge score is **not** ground truth. It is a model's opinion under a
rubric and must be validated against human review before being treated as
authoritative.

## Statistical treatment

- Per-dimension and per-category means are descriptive.
- Model comparison uses a **paired** comparison on the intersection of examples
  evaluated by both jobs, with a bootstrap 95% confidence interval
  (`app/evaluation/aggregation.py`). The seed is fixed for reproducibility.
- A confidence interval that includes zero does **not** support a claim that one
  model is better. TEB does not compute significance tests beyond the interval;
  do not describe differences as "significant" on that basis alone.

## Fair comparison checklist

Before comparing two models, confirm:

- [ ] same dataset version and content hash;
- [ ] same partition / example subset (TEB reports the intersection);
- [ ] same prompt version and rubric version;
- [ ] same decoding settings (temperature, max_tokens);
- [ ] same provider-reported model identifier (record the exact string);
- [ ] cost and latency recorded where the provider reports them;
- [ ] human/judge provenance labelled on every dimension used.

## Known limitations of automatic Tamil evaluation

- **Morphology.** Tamil is agglutinative; surface matching under-detects correct
  inflected forms. Glossary matching includes heuristic variants, which is
  approximate.
- **Word order.** Valid answers may reorder clauses; overlap metrics penalise this
  even when meaning is intact.
- **Transliteration.** Romanization is non-standard; many spellings are valid.
- **No true entailment.** Nothing here proves that a response *entails* the
  source. Deterministic proxies are evidence, not proof.
- **Script handling.** Mixed-script and romanized inputs are the hardest case and
  the least reliable to score automatically.
- **Judge bias.** An LLM judge may favour fluent output over faithful output, and
  may be biased toward the reference style.

## Reproducing a result

```bash
teb doctor
teb dataset build
teb dataset import benchmark/data/v1.0.0/examples.jsonl
teb eval run --provider mock --name reproduce-demo      # deterministic, $0.00
teb eval report --job <id> --format markdown
```

Every report header records the dataset version and content hash, provider and
model id, prompt and rubric versions, decoding config, code revision, and cost,
so a reader can tell exactly what produced the numbers.
