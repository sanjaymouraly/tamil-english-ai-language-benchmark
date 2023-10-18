"""Terminology Consistency scorer.

Two independent signals:

1. Within-example glossary adherence: for each glossary term whose
   source form appears in the source text, does the response use the
   preferred translation (or an approved variant)?

2. Cross-example consistency (computed at job level): for each glossary
   concept, the set of distinct translations used across all responses
   in the job must be a single variant. Multiple variants -> penalty.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.schemas import BenchmarkExample, GlossaryTerm
from app.evaluation.text_utils import normalize_for_match


@dataclass
class TermHit:
    term: str
    expected: str
    found: str | None
    hit: bool


@dataclass
class TerminologyResult:
    score: float | None
    available: bool = True
    applicable_terms: int = 0
    hits: int = 0
    term_details: list[TermHit] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    consistency_penalty: float = 1.0


def term_variants(term: GlossaryTerm) -> list[str]:
    """Approved surface variants of the preferred translation."""
    base = term.translation.strip()
    variants = {base}
    # Tamil inflection tolerance: allow common case-ending suffixes.
    if any("\u0b80" <= ch <= "\u0bff" for ch in base):
        for suffix in (
            "இ",
            "உ",
            "அ",
            "ம்",
            "ல்",
            "க்கு",
            "ஐ",
            "து",
            "தால்",
            "ஆ",
            "கள்",
            "கிற",
            "ச்",
            "த்த",
        ):
            variants.add(base + suffix)
        # Also allow the stem alone when base ends in a common suffix.
        for suffix in ("ம்", "ல்", "து", "கள்", "ஐ", "உ"):
            if base.endswith(suffix) and len(base) > len(suffix):
                variants.add(base[: -len(suffix)])
    # English plural/case tolerance.
    if base.isascii():
        variants.add(base.rstrip("s"))
        variants.add(base + "s")
    return sorted(variants, key=len, reverse=True)


def term_in_response(term: GlossaryTerm, response: str) -> str | None:
    """Return the variant found in the response, or None."""
    resp = normalize_for_match(response)
    for variant in term_variants(term):
        if normalize_for_match(variant) in resp:
            return variant
    return None


def source_contains(term: GlossaryTerm, source: str) -> bool:
    """Does the source text contain the term's source form?"""
    src = normalize_for_match(source)
    return normalize_for_match(term.term) in src


def glossary_adherence(example: BenchmarkExample, response: str) -> TerminologyResult:
    """Score glossary adherence for a single example."""
    applicable: list[TermHit] = []
    for term in example.glossary:
        if (
            source_contains(term, example.source_text)
            or source_contains(term, response)
            or term.language == "en"
        ):
            # English-source terms: apply when the English term appears in
            # the source OR the response is expected to be Tamil (en->ta).
            # Only require the English term when the source is English (en->ta tasks).
            if (
                term.language == "en"
                and not source_contains(term, example.source_text)
                and "->ta" not in example.direction
                and "en" not in example.source_language
            ):
                continue
            found = term_in_response(term, response)
            applicable.append(
                TermHit(
                    term=term.term, expected=term.translation, found=found, hit=found is not None
                )
            )
    if not applicable:
        return TerminologyResult(score=None, available=False, applicable_terms=0)
    hits = sum(1 for t in applicable if t.hit)
    score = hits / len(applicable)
    evidence = [f"missed '{t.term}' -> expected '{t.expected}'" for t in applicable if not t.hit]
    return TerminologyResult(
        score=round(score, 4),
        available=True,
        applicable_terms=len(applicable),
        hits=hits,
        term_details=applicable,
        evidence=evidence,
    )


def cross_example_consistency(
    results: list[tuple[BenchmarkExample, str, list[GlossaryTerm]]],
) -> dict[str, object]:
    """Compute job-level terminology consistency across all responses.

    `results` is a list of (example, response, glossary) triples.
    For every glossary concept, collect the surface translations used;
    if more than one distinct variant appears, the concept is unstable.
    """
    concept_usage: dict[str, set[str]] = {}
    for _example, response, glossary in results:
        for term in glossary:
            used = set()
            resp = normalize_for_match(response)
            for variant in term_variants(term):
                if normalize_for_match(variant) in resp:
                    used.add(variant)
            if used:
                concept_usage.setdefault(term.term, set()).update(used)
    unstable = {c: sorted(v) for c, v in concept_usage.items() if len(v) > 1}
    stable = len(concept_usage) - len(unstable)
    factor = (stable / len(concept_usage)) if concept_usage else 1.0
    return {
        "concepts_seen": len(concept_usage),
        "unstable_concepts": unstable,
        "consistency_factor": round(factor, 4),
    }
