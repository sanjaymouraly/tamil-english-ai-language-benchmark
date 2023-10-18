"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import reset_settings_cache
from app.core.schemas import BenchmarkExample, Category, Difficulty, ScriptKind


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Point every test at a temporary data dir and DB."""
    monkeypatch.setenv("TEB_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("TEB_DB_PATH", str(tmp_path / "data" / "test.db"))
    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture()
def db_session():
    from app.database.session import init_db, reset_db, session_scope

    init_db()
    with session_scope() as session:
        yield session
    reset_db()


def make_example(**overrides) -> BenchmarkExample:
    """Build a minimal valid example for tests."""
    base = dict(
        id="TEB-TST-0001",
        category=Category.TRANSLATION_TA_TO_EN.value
        if hasattr(Category, "TRANSLATION_TA_TO_EN")
        else "translation_ta_to_en",
        task_type="translation",
        direction="ta->en",
        source_text="நான் பள்ளிக்குப் போகிறேன்.",
        source_script=ScriptKind.TAMIL.value,
        expected_behavior="Translate to English.",
        references=["I am going to school."],
        difficulty=Difficulty.EASY.value,
    )
    base.update(overrides)
    return BenchmarkExample.model_validate(base)


def write_jsonl(path: Path, examples: list[BenchmarkExample]) -> Path:
    import json

    with path.open("w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(json.dumps(ex.model_dump(mode="json"), ensure_ascii=False) + "\n")
    return path
