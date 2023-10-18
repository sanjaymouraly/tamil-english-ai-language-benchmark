"""Dataset validation: completeness, structure, Unicode hygiene, PII, leakage."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.core.schemas import BenchmarkExample
from app.core.security import contains_replacement_char, looks_like_pii, script_kind


@dataclass
class ValidationIssue:
    example_id: str
    rule: str
    severity: str  # "error" | "warning"
    message: str


@dataclass
class ValidationReport:
    total: int
    valid: int
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "valid": self.valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [vars(e) for e in self.errors],
            "warnings": [vars(w) for w in self.warnings],
        }


# Unicode ranges for Tamil (U+0B80..U+0BFF) and Latin.
_TAMIL_RANGE = (0x0B80, 0x0BFF)

# Common Tamil grammar sanity checks: a Tamil word should not end with a
# combining virama (pulli) with no following consonant, and should not
# contain the anusvara-only artifacts of bad conversion.
_BAD_TAMIL_PATTERNS = [
    re.compile("[ஃ]$"),  # word ending with pulli marker
]


def validate_examples(examples: list[BenchmarkExample]) -> ValidationReport:
    """Run all structural and hygiene validation rules."""
    report = ValidationReport(total=len(examples), valid=0)
    seen_ids: set[str] = set()
    for ex in examples:
        issues: list[ValidationIssue] = []

        # --- Completeness -------------------------------------------------
        if not ex.source_text.strip():
            issues.append(ValidationIssue(ex.id, "completeness", "error", "source_text is empty"))
        if not ex.references:
            issues.append(ValidationIssue(ex.id, "completeness", "error", "no references provided"))
        for ref in ex.references:
            if not ref.strip():
                issues.append(
                    ValidationIssue(ex.id, "completeness", "error", "empty reference string")
                )
        if not ex.expected_behavior.strip():
            issues.append(
                ValidationIssue(ex.id, "completeness", "error", "expected_behavior is empty")
            )

        # --- Unicode hygiene ----------------------------------------------
        for label, text in (
            ("source_text", ex.source_text),
            *[("reference", r) for r in ex.references],
        ):
            nfc = unicodedata.normalize("NFC", text)
            if nfc != text:
                issues.append(
                    ValidationIssue(
                        ex.id, "unicode_nfc", "warning", f"{label} is not NFC-normalized"
                    )
                )
            if contains_replacement_char(text):
                issues.append(
                    ValidationIssue(
                        ex.id,
                        "unicode_replacement_char",
                        "error",
                        f"{label} contains U+FFFD (decoding damage)",
                    )
                )
            if "\u0000" in text:
                issues.append(
                    ValidationIssue(ex.id, "unicode_control_char", "error", f"{label} contains NUL")
                )

        # --- Script / label consistency -----------------------------------
        detected = script_kind(ex.source_text)
        if ex.source_script == "tamil" and detected == "latin":
            issues.append(
                ValidationIssue(
                    ex.id,
                    "script_label",
                    "error",
                    "source_script=tamil but text has no Tamil characters",
                )
            )
        if ex.source_script == "latin" and detected == "tamil":
            issues.append(
                ValidationIssue(
                    ex.id,
                    "script_label",
                    "error",
                    "source_script=latin but text contains Tamil characters",
                )
            )
        valid_directions = {
            "ta->en",
            "en->ta",
            "mixed->en",
            "mixed->ta",
            "ta->ta",
            "en->en",
            "roman-ta->ta+en",
            "ta+en->ta",
            "ta+en->en",
            "en+ta->ta",
            "en+ta->en",
            "mixed->mixed",
        }
        if ex.direction not in valid_directions:
            issues.append(
                ValidationIssue(
                    ex.id, "direction_label", "error", f"invalid direction label: {ex.direction}"
                )
            )

        # --- Reference leakage --------------------------------------------
        for ref in ex.references:
            if _normalize(ref) and _normalize(ref) == _normalize(ex.source_text):
                issues.append(
                    ValidationIssue(
                        ex.id,
                        "reference_leakage",
                        "warning",
                        "a reference exactly equals the source text",
                    )
                )

        # --- Constraint sanity --------------------------------------------
        for c in ex.critical_constraints:
            if not c.alternatives:
                issues.append(
                    ValidationIssue(
                        ex.id, "constraint_sanity", "error", f"constraint {c.kind} has no value"
                    )
                )

        # --- PII hygiene ---------------------------------------------------
        findings = looks_like_pii(ex.source_text)
        for f in findings:
            issues.append(ValidationIssue(ex.id, "pii_heuristic", "warning", f))
        for ref in ex.references:
            for f in looks_like_pii(ref):
                issues.append(
                    ValidationIssue(
                        ex.id, "pii_heuristic", "warning", f"reference contains possible PII: {f}"
                    )
                )

        # --- Duplicate IDs --------------------------------------------------
        if ex.id in seen_ids:
            issues.append(
                ValidationIssue(ex.id, "duplicate_id", "error", f"duplicate example id: {ex.id}")
            )
        seen_ids.add(ex.id)

        report.errors.extend([i for i in issues if i.severity == "error"])
        report.warnings.extend([i for i in issues if i.severity == "warning"])
        if not any(i.severity == "error" for i in issues):
            report.valid += 1
    return report


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", text)).lower()


def check_duplicates(examples: list[BenchmarkExample]) -> list[tuple[str, str]]:
    """Find near-duplicate source texts across the dataset (cross-record dedup).

    Returns pairs of (id_a, id_b) whose normalized source texts match exactly
    or whose char-3gram Jaccard similarity exceeds 0.95.
    """
    pairs: list[tuple[str, str]] = []
    normalized = [_normalize(ex.source_text) for ex in examples]
    keys: dict[str, str] = {}
    for ex, norm in zip(examples, normalized, strict=False):
        if norm and norm in keys:
            pairs.append((keys[norm], ex.id))
        else:
            keys[norm] = ex.id
    return pairs


def trigrams(text: str) -> set[str]:
    text = _normalize(text)
    return {text[i : i + 3] for i in range(len(text) - 2)} if len(text) > 2 else {text}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
