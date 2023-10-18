# Annotation guidelines (TEB v1.0.0)

These guidelines define how a human reviewer should score a model response for a
Tamil–English benchmark example. They exist so that independent reviewers can
produce comparable annotations, and so that disagreements are informative rather
than accidental.

> **Status of the shipped dataset:** every record is synthetic and
> `machine_validated`. No human annotation has been applied. These guidelines are
> the process to follow when human review *is* performed.

## What you are scoring

For each example you see the source text, the expected behaviour, one or more
acceptable references, optional glossary/terminology expectations, and the
model's response. Score the response on each dimension independently — do not
let a good score on one dimension pull up another.

### 1. Semantic preservation (0–1)

Does the response convey the same meaning as the source, including:

- the main proposition;
- **negation** (a dropped "not" is a hard failure);
- who did what to whom (subject/object roles);
- quantities, times, dates, units;
- modality (must / may / can) and tense.

| Score | Meaning |
| --- | --- |
| 1.0 | Meaning fully preserved; any difference is stylistic. |
| 0.75 | Minor detail altered or omitted; main meaning intact. |
| 0.5 | Part of the meaning survives; a significant fact is wrong or missing. |
| 0.25 | Meaning largely lost; only fragments survive. |
| 0.0 | Meaning reversed, unrelated, or empty. |

### 2. Terminology consistency (0–1)

Only score this when the example defines glossary terms. Check that each term
uses an approved surface form (inflected variants of an approved form count as
correct).

| Score | Meaning |
| --- | --- |
| 1.0 | Every applicable term uses an approved form. |
| 0.5 | Some terms correct, some not. |
| 0.0 | Terms systematically wrong. |
| n/a | No glossary terms apply — leave blank, do not enter 0. |

### 3. Fluency / naturalness (0–1)

Would a native speaker write this? Grammar, agreement, word order, idiom.
Ignore meaning errors here (they are captured under semantic preservation).

### 4. Adequacy (0–1)

Overall fitness for the stated task (translate / summarize / answer / continue
a dialogue), including whether the requested output language and format were
respected.

### 5. Cultural suitability (0–1)

Honorifics, politeness level, kinship terms, idioms, and culturally loaded
expressions handled appropriately for the stated context.

## Reference outputs are not the only correct answer

Tamil allows word-order variation, inflectional richness, and multiple valid
lexical choices. If a response is correct but differs from the reference, score
it on meaning — **do not** penalise it for not matching the reference string.
Flag genuinely new acceptable paraphrases in your notes so they can be added as
additional references.

## Register

Match the register expected by the example (`formal`, `informal`, `neutral`).
Using casual Tamil where the context requires respect (or vice versa) is a real
error and belongs under cultural suitability and/or adequacy.

## Disagreement and adjudication

1. Each reviewer scores independently and records a status
   (`pending` / `approved` / `disputed`).
2. When two reviewers disagree on a dimension by more than 0.25, mark the record
   `disputed`.
3. An adjudicator reviews the disagreement, records a decision
   (`uphold` / `override` / `revise`) and final scores, and sets the record to
   `adjudicated`.
4. Never overwrite another reviewer's scores — add your own review.

## Honesty requirements

- Do not mark a record `human_reviewed` unless a named human actually reviewed it.
- Do not invent reviewer identities or scores.
- Record your name, the date, and free-text notes explaining non-obvious calls.
- If you are unsure, say so and mark the record `disputed` rather than guessing.
