"""Security helpers: safe filenames, upload limits, input sanitisation."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_MAX_FILENAME_LEN = 120
_ALLOWED_DATA_EXTENSIONS = {".jsonl", ".json", ".csv", ".parquet"}


def safe_filename(name: str) -> str:
    """Return a filename safe for storage: no traversal, no weird characters."""
    # Strip any directory components the caller may have smuggled in.
    name = Path(name).name
    name = unicodedata.normalize("NFC", name).strip()
    name = re.sub(r"[^\w.\- ]", "_", name)
    name = name.replace(" ", "_")
    if len(name) > _MAX_FILENAME_LEN:
        stem, dot, ext = name.rpartition(".")
        name = stem[: _MAX_FILENAME_LEN - len(dot) - len(ext)] + dot + ext
    if not name or name in {".", ".."}:
        raise ValueError("invalid filename")
    return name


def validate_data_file(path: Path) -> None:
    """Ensure an uploaded data file has an allowed extension and sane size."""
    if path.suffix.lower() not in _ALLOWED_DATA_EXTENSIONS:
        raise ValueError(
            f"unsupported file type '{path.suffix}'; allowed: {sorted(_ALLOWED_DATA_EXTENSIONS)}"
        )
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > 50:
            raise ValueError(f"file too large ({size_mb:.1f} MB); limit is 50 MB")


def looks_like_pii(text: str) -> list[str]:
    """Heuristic PII detection used by dataset hygiene checks.

    Flags phone-like numbers, emails, and 10-12 digit identifiers (e.g. Aadhaar-like).
    Returns a list of human-readable findings (empty when clean).
    """
    findings: list[str] = []
    if re.search(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", text):
        findings.append("email address detected")
    if re.search(r"\b(?:\+?\d[\d\s\-]{7,}\d)\b", text):
        findings.append("phone-number-like sequence detected")
    if re.search(r"\b\d{10,12}\b", text):
        findings.append("long digit sequence (possible national ID) detected")
    return findings


def contains_replacement_char(text: str) -> bool:
    """True when text contains the Unicode replacement char (decoding damage)."""
    return "�" in text


def script_kind(text: str) -> str:
    """Classify the dominant script of a text: 'tamil', 'latin', or 'mixed'."""
    has_tamil = any("\u0b80" <= ch <= "\u0bff" for ch in text)
    has_latin = any("a" <= ch <= "z" or "A" <= ch <= "Z" for ch in text)
    if has_tamil and has_latin:
        return "mixed"
    if has_tamil:
        return "tamil"
    if has_latin:
        return "latin"
    return "latin"
