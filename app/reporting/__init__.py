"""Reporting: Markdown, JSON, CSV, and self-contained HTML reports."""

from __future__ import annotations


def category_from_id(example_id: str) -> str:
    """Fallback category label derived from an example id.

    Example ids look like ``TEB-T2E-0001``. This is only used when the real
    category is unavailable (e.g. the example row was deleted); callers should
    prefer the authoritative category from the dataset.
    """
    parts = example_id.split("-")
    return parts[1] if len(parts) > 1 else "other"
