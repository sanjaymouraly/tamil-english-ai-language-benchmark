"""Unit tests for the safe .env read/merge helper."""

from __future__ import annotations

import pytest

from app.core.envfile import mask_secret, read_env_file, update_env_file


def test_read_missing_file_returns_empty(tmp_path):
    assert read_env_file(tmp_path / "nope.env") == {}


def test_update_creates_file(tmp_path):
    path = tmp_path / ".env"
    written = update_env_file(path, {"OPENAI_API_KEY": "sk-abc"})
    assert written == ["OPENAI_API_KEY"]
    assert read_env_file(path)["OPENAI_API_KEY"] == "sk-abc"


def test_update_replaces_in_place_and_preserves_other_lines(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        "# a comment\nTEB_ENV=development\nOPENAI_API_KEY=old\nUNRELATED=keep\n",
        encoding="utf-8",
    )
    update_env_file(path, {"OPENAI_API_KEY": "new"})
    text = path.read_text(encoding="utf-8")
    assert "# a comment" in text
    assert "UNRELATED=keep" in text
    assert "OPENAI_API_KEY=new" in text
    assert "OPENAI_API_KEY=old" not in text


def test_update_appends_new_keys(tmp_path):
    path = tmp_path / ".env"
    path.write_text("TEB_ENV=development\n", encoding="utf-8")
    update_env_file(path, {"OLLAMA_MODEL": "qwen3.5:4b"})
    values = read_env_file(path)
    assert values["TEB_ENV"] == "development"
    assert values["OLLAMA_MODEL"] == "qwen3.5:4b"


def test_update_rejects_invalid_key_names(tmp_path):
    with pytest.raises(ValueError):
        update_env_file(tmp_path / ".env", {"bad-key!": "x"})
    with pytest.raises(ValueError):
        update_env_file(tmp_path / ".env", {"1LEADING": "x"})


def test_read_handles_export_and_quotes(tmp_path):
    path = tmp_path / ".env"
    path.write_text("export FOO=\"bar baz\"\nQUOTED='single'\n", encoding="utf-8")
    values = read_env_file(path)
    assert values["FOO"] == "bar baz"
    assert values["QUOTED"] == "single"


def test_mask_secret_never_reveals_full_value():
    assert mask_secret("") == ""
    assert set(mask_secret("short")) == {"*"}
    masked = mask_secret("sk-abcdefghijklmnop")
    assert "abcdefghijklmnop" not in masked
