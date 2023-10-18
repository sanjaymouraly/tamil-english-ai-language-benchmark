# Human annotation & adjudication

Machine scores are a first pass. This layer records human judgement and lets
reviewers resolve disagreement.

## Verification levels

Every record and score is labelled with one of:

- **`machine_validated`** — checked only by deterministic rules
- **`agent_reviewed`** — reviewed by an automated agent / LLM judge
- **`human_reviewed`** — a human reviewer recorded scores
- **`adjudicated`** — a second human resolved a dispute

These levels are never conflated; a dashboard or report always states which
level a number came from.

## Workflow

1. **Annotate** — a reviewer records per-dimension scores for an example and
   whether they agree with the machine result (`agrees_with_machine`).
2. **Status** — each review is `pending`, `approved`, or `disputed`.
3. **Adjudicate** — when ≥2 reviews disagree (score spread > 0.3) or any review
   is disputed, an adjudicator records a final decision.
4. **Summary** — `annotation status` reports coverage, agreement rate, and
   disagreement count per example.

## API / CLI

```bash
# read
teb annotation status
# API: GET /annotations/status, GET /annotations/{example_id}

# write — record a review
teb annotation review TEB-T2E-0001 --reviewer alice \
    --semantic 0.9 --terminology 0.8 --status approved
# API: POST /annotations/review

# write — resolve a dispute
teb annotation adjudicate TEB-T2E-0001 --adjudicator bob \
    --decision override --notes "machine missed context"
# API: POST /annotations/adjudicate
```

Adjudication decisions: `uphold`, `override`, `revise`.

The annotation service (`app/annotation/service.py`) persists
`ReviewRecord` and `AdjudicationRecord` rows and computes a `ReviewSummary`
that marks an example `approved` only when all reviews agree and none are
disputed.

## Honest labelling

The shipped dataset is **synthetic / AI-generated** and currently only
`machine_validated`. No human annotations are bundled. Any human review you add
is stored in your own database and clearly marked `human_reviewed` or
`adjudicated`.
