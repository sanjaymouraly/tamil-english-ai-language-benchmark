"""Additional deterministic metrics: script validity, fluency heuristics,
transliteration accuracy, and structural checks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.schemas import BenchmarkExample
from app.core.security import contains_replacement_char, script_kind
from app.evaluation.text_utils import (
    edit_similarity,
    tamil_ratio,
)


@dataclass
class ScriptValidityResult:
    score: float
    expected_script: str
    detected_script: str
    evidence: list[str]


def script_validity_score(example: BenchmarkExample, response: str) -> ScriptValidityResult:
    """Check that the response script matches the expected target script.

    Target script is derived from the example's target_language:
    ta -> Tamil script, en -> Latin script, mixed -> either.
    """
    text = response.strip()
    if not text:
        return ScriptValidityResult(0.0, example.target_language, "empty", ["empty response"])

    target = example.target_language
    detected = script_kind(text)
    evidence: list[str] = []

    if target in {"ta", "ta+en"}:
        ratio = tamil_ratio(text)
        if ratio >= 0.3:
            return ScriptValidityResult(1.0, "tamil", detected, [])
        if ratio > 0.0:
            evidence.append(f"only {ratio:.0%} Tamil characters in response")
            return ScriptValidityResult(0.5, "tamil", detected, evidence)
        evidence.append("no Tamil script in a Tamil-target response")
        return ScriptValidityResult(0.0, "tamil", detected, evidence)
    if target == "en":
        ratio = tamil_ratio(text)
        if ratio <= 0.05:
            return ScriptValidityResult(1.0, "latin", detected, [])
        evidence.append(f"unexpected Tamil script ratio {ratio:.0%} in English-target response")
        return ScriptValidityResult(0.5, "latin", detected, evidence)
    # mixed targets: accept either script
    return ScriptValidityResult(1.0, "mixed", detected, [])


def fluency_heuristics(response: str) -> tuple[float, list[str]]:
    """Cheap, honest fluency heuristics (NOT a fluency judgment).

    Flags mechanical defects only: empty output, runaway character
    repetition, unbalanced quotes/brackets, mojibake, and repeated
    word runs. Score 1.0 when no defect is detected; the metric is
    explicitly marked as a heuristic in the output.
    """
    text = response.strip()
    evidence: list[str] = []
    if not text:
        return 0.0, ["empty response"]
    if contains_replacement_char(text):
        evidence.append("contains U+FFFD replacement character (encoding damage)")
    # Runaway repetition of a single character (e.g. 'aaaaaa').
    if re.search(r"(.)\1{9,}", text):
        evidence.append("character repeated 10+ times")
    # Repeated word runs (e.g. 'the the the the').
    if re.search(r"\b(\w+)\s+\1\s+\1\s+\1\b", text, flags=re.IGNORECASE):
        evidence.append("word repeated 4+ times in a row")
    # Unbalanced quotes/brackets (report every affected pair).
    for open_ch, close_ch in (("(", ")"), ("[", "]"), ('"', '"'), ("'", "'")):
        if text.count(open_ch) != text.count(close_ch):
            evidence.append(f"unbalanced '{open_ch}{close_ch}'")
    score = 1.0 - 0.25 * len(evidence)
    return max(score, 0.0), evidence


def transliteration_score(example: BenchmarkExample, response: str) -> tuple[float, dict]:
    """For romanized-Tamil tasks: script accuracy + romanization fidelity.

    - script_accuracy: does the response contain the Tamil-script form?
    - romanization_fidelity: normalized edit similarity between the
      source romanization and the response's romanized content.
    """
    source = example.source_text
    tamil_present = tamil_ratio(response) > 0.3
    script_accuracy = 1.0 if tamil_present else 0.0

    # Romanization fidelity: compare against references when they carry
    # romanized Tamil; otherwise compare with the source itself.
    roman_candidates = [source] + [r for r in example.references if "(" in r and "த" in r]
    best = 0.0
    for cand in roman_candidates:
        # Extract latin parts from the reference (in parentheses) if any.
        if "(" in cand:
            inner = re.findall(r"\(([^)]+)\)", cand)
            cand_text = " ".join(inner)
        else:
            cand_text = cand
        sim = edit_similarity(response, cand_text)
        best = max(best, sim)
    score = 0.5 * script_accuracy + 0.5 * best
    detail = {
        "tamil_script_present": tamil_present,
        "romanization_fidelity": round(best, 4),
    }
    return round(score, 4), detail


def structure_check(response: str, requirement: str) -> float:
    """Simple structural requirement checks (e.g. 'list', 'json')."""
    text = response.strip()
    if requirement == "list":
        lines = [ln for ln in text.splitlines() if ln.strip()]
        markers = sum(1 for ln in lines if re.match(r"^\s*([0-9]+[.):]|[-•*]|\d+\))", ln))
        return 1.0 if markers >= 2 else (0.5 if markers == 1 else 0.0)
    if requirement == "json":
        try:
            import json

            json.loads(text)
            return 1.0
        except json.JSONDecodeError:
            return 0.0
    return 1.0
