"""Deterministic constraint checking (Layer 1 of the evaluation)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.schemas import BenchmarkExample, CriticalConstraint
from app.evaluation.text_utils import extract_numbers, normalize_for_match


@dataclass
class ConstraintCheck:
    constraint: CriticalConstraint
    passed: bool
    detail: str

    @property
    def kind(self) -> str:
        return self.constraint.kind.value


def check_constraint(constraint: CriticalConstraint, source: str, response: str) -> ConstraintCheck:
    """Check one critical constraint against a model response."""
    kind = constraint.kind.value
    if kind == "must_contain":
        for alt in constraint.alternatives:
            if _contains(response, alt):
                return ConstraintCheck(constraint, True, f"found '{alt}'")
        return ConstraintCheck(constraint, False, f"none of {constraint.alternatives} found")
    if kind == "must_not_contain":
        for alt in constraint.alternatives:
            if _contains(response, alt):
                return ConstraintCheck(constraint, False, f"forbidden '{alt}' present")
        return ConstraintCheck(constraint, True, "forbidden strings absent")
    if kind == "regex":
        try:
            flags = re.UNICODE | re.MULTILINE
            if any(re.search(p, response, flags) for p in constraint.alternatives):
                return ConstraintCheck(constraint, True, "regex matched")
        except re.error:
            return ConstraintCheck(constraint, False, f"invalid regex: {constraint.alternatives}")
        return ConstraintCheck(constraint, False, "regex did not match")
    if kind == "numeric_preservation":
        value = constraint.alternatives[0]
        resp_numbers = extract_numbers(response)
        if _number_matches(value, resp_numbers):
            return ConstraintCheck(constraint, True, f"number {value} preserved")
        return ConstraintCheck(constraint, False, f"number {value} missing or altered")
    if kind == "entity_preservation":
        value = constraint.alternatives[0]
        if _contains(response, value):
            return ConstraintCheck(constraint, True, f"entity '{value}' preserved")
        return ConstraintCheck(constraint, False, f"entity '{value}' missing")
    return ConstraintCheck(constraint, False, f"unknown constraint kind: {kind}")


def _contains(response: str, needle: str) -> bool:
    if not needle:
        return False
    resp = normalize_for_match(response)
    # Match the needle literally (normalized) OR any stem variant when
    # the needle ends with a Tamil stem marker we cannot detect; plain
    # substring works because constraints are authored as stems.
    return normalize_for_match(needle) in resp


def _number_matches(expected: str, found: list[str]) -> bool:
    # Decimal variants like 6.45 vs 6:45 are handled by times separately.
    exp = expected.replace(",", "")
    return any(num.replace(",", "") == exp for num in found)


def check_all_constraints(example: BenchmarkExample, response: str) -> list[ConstraintCheck]:
    return [
        check_constraint(c, example.source_text, response) for c in example.critical_constraints
    ]


def constraint_score(
    example: BenchmarkExample, response: str
) -> tuple[float, list[ConstraintCheck]]:
    """Fraction of constraints satisfied (1.0 when no constraints defined)."""
    if not example.critical_constraints:
        return 1.0, []
    checks = check_all_constraints(example, response)
    passed = sum(1 for c in checks if c.passed)
    return passed / len(checks), checks


def numeric_preservation_score(example: BenchmarkExample, response: str) -> tuple[float, dict]:
    """Check that numbers/dates/times/units from the source survive.

    Only numbers with semantic weight are considered: we skip numbers
    that also appear inside reference-neutral contexts like example ids.
    """
    source_entities = [e for e in _semantic_numbers(example.source_text)]
    if not source_entities:
        return 1.0, {"source_entities": [], "missing": [], "found": []}
    resp_numbers = extract_numbers(response)
    resp_times = set(re.findall(r"\d{1,2}[:.]\d{2}", response))
    resp_dates = set(re.findall(r"\d{1,2}\s+\S+", normalize_for_match(response)))
    missing = []
    for ent in source_entities:
        if ent in resp_numbers or ent in resp_times or ent in resp_dates:
            continue
        # tolerate Tamil word numerals for small digits
        tamil_variant = _tamil_numeral_variant(ent)
        if tamil_variant and tamil_variant in response:
            continue
        missing.append(ent)
    score = (len(source_entities) - len(missing)) / len(source_entities)
    return score, {"source_entities": source_entities, "missing": missing}


def _semantic_numbers(text: str) -> list[str]:
    """Numbers extracted from the source that must survive translation.

    Every number in the source text is treated as meaningful: this benchmark
    authors source text deliberately, so digits in it (times, quantities,
    invoice ids, order numbers) are content rather than incidental markup.
    """
    return list(extract_numbers(text))


_TAMIL_DIGITS = {
    "0": "௦",
    "1": "௧",
    "2": "௨",
    "3": "௩",
    "4": "௪",
    "5": "௫",
    "6": "௬",
    "7": "௭",
    "8": "௮",
    "9": "௯",
}


def _tamil_numeral_variant(number: str) -> str | None:
    digits = number.replace(",", "")
    if digits.isdigit() and len(digits) <= 3:
        return "".join(_TAMIL_DIGITS[d] for d in digits)
    return None
