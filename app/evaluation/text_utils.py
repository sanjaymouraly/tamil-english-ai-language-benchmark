"""Text normalization and tokenization utilities (Tamil + English)."""

from __future__ import annotations

import re
import unicodedata

TAMIL_RANGES = [("\u0b80", "\u0bff")]


def normalize_nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def normalize_for_match(text: str) -> str:
    """Aggressive normalization for robust matching.

    Lowercases, strips punctuation, collapses whitespace, removes
    Tamil pulli-dependent vowel sign differences where safe, and
    normalizes digit grouping separators.
    """
    text = normalize_nfc(text)
    text = text.lower()
    # Treat Tamil punctuation like whitespace.
    text = re.sub(r"[!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~·।॥]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tamil_ratio(text: str) -> float:
    """Fraction of alphabetic characters that are Tamil."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    tamil = [ch for ch in letters if "\u0b80" <= ch <= "\u0bff"]
    return len(tamil) / len(letters)


def word_tokens(text: str) -> list[str]:
    """Split text into word tokens (language-agnostic, whitespace based)."""
    return re.findall(r"\w+", normalize_for_match(text))


def char_ngrams(text: str, n: int = 3) -> set[str]:
    text = normalize_for_match(text)
    return {text[i : i + n] for i in range(max(len(text) - n + 1, 0))}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def token_f1(candidate: str, reference: str) -> float:
    """Token-level F1 between candidate and reference (English-ish)."""
    cand = word_tokens(candidate)
    ref = word_tokens(reference)
    if not cand or not ref:
        return 0.0
    common: dict[str, int] = {}
    for tok in cand:
        common[tok] = common.get(tok, 0) + 1
    overlap = 0
    for tok in ref:
        if common.get(tok, 0) > 0:
            overlap += 1
            common[tok] -= 1
    precision = overlap / len(cand)
    recall = overlap / len(ref)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def best_reference_similarity(response: str, references: list[str]) -> float:
    """Best similarity of the response against any acceptable reference.

    Tamil-dominant text is compared with character 3-gram Jaccard
    (robust to inflection and word order); Latin-dominant text uses
    token F1. The blend of both is used when scripts are mixed.
    """
    best = 0.0
    for ref in references:
        t_ratio = tamil_ratio(response + " " + ref)
        char_sim = jaccard(char_ngrams(response, 3), char_ngrams(ref, 3))
        tok_sim = token_f1(response, ref)
        if t_ratio > 0.5:  # Tamil-dominant: char n-grams handle morphology
            sim = 0.75 * char_sim + 0.25 * tok_sim
        elif t_ratio < 0.05:  # Latin-dominant
            sim = 0.7 * tok_sim + 0.3 * char_sim
        else:  # mixed scripts
            sim = 0.5 * char_sim + 0.5 * tok_sim
        best = max(best, sim)
    return best


def edit_similarity(a: str, b: str) -> float:
    """Normalized Levenshtein similarity (1 = identical)."""
    a_n = re.sub(r"[^a-z0-9]", "", a.lower())
    b_n = re.sub(r"[^a-z0-9]", "", b.lower())
    if not a_n and not b_n:
        return 1.0
    if not a_n or not b_n:
        return 0.0
    # Dynamic-programming Levenshtein.
    prev = list(range(len(b_n) + 1))
    for i, ca in enumerate(a_n, 1):
        cur = [i]
        for j, cb in enumerate(b_n, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    dist = prev[-1]
    return 1.0 - dist / max(len(a_n), len(b_n))


# ---------------------------------------------------------------------------
# Numeric / date / unit extraction
# ---------------------------------------------------------------------------

_MONTHS_TA = {
    "ஜனவரி",
    "பிப்ரவரி",
    "மார்ச்",
    "ஏப்ரல்",
    "மே",
    "சூன்",
    "சூலை",
    "ஆகஸ்ட்",
    "செப்டம்பர்",
    "அக்டோபர்",
    "நவம்பர்",
    "திசம்பர்",
}
_MONTHS_EN = {
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
}

_NUM_RE = re.compile(r"\d[\d,]*\.?\d*")
_TIME_RE = re.compile(r"\d{1,2}[:.]\d{2}")
_DATE_RE = re.compile(
    r"\d{1,2}\s+(?:மார்ச்|ஜனவரி|பிப்ரவரி|ஏப்ரல்|மே|சூன்|சூலை|ஆகஸ்ட்|செப்டம்பர்|அக்டோபர்|நவம்பர்|திசம்பர்|January|February|March|April|May|June|July|August|September|October|November|December)",
    re.IGNORECASE,
)
_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:கி\.மீ|கிமீ|கி\.மீ\.|km|KM|கிலோ|kg|KG|லிட்டர்|litre|liter|L|மீ|cm|மி\.லி|ml|mL|கிராம்|gram|g)",
    re.IGNORECASE,
)


def extract_numbers(text: str) -> list[str]:
    """Extract numeric values, normalized (commas removed)."""
    out: list[str] = []
    for m in _NUM_RE.finditer(text):
        raw = m.group(0)
        norm = raw.replace(",", "")
        out.append(norm)
    return out


def extract_dates(text: str) -> list[str]:
    return [m.group(0) for m in _DATE_RE.finditer(text)]


def extract_times(text: str) -> list[str]:
    return [m.group(0) for m in _TIME_RE.finditer(text)]


def extract_units(text: str) -> list[str]:
    return [m.group(0).strip() for m in _UNIT_RE.finditer(text)]


def numeric_entities(text: str) -> list[str]:
    """All numeric-ish entities (numbers, times, dates, units)."""
    found: list[str] = []
    for item in (
        extract_numbers(text) + extract_times(text) + extract_dates(text) + extract_units(text)
    ):
        norm = re.sub(r"\s+", " ", item).strip()
        if norm and norm not in found:
            found.append(norm)
    return found
