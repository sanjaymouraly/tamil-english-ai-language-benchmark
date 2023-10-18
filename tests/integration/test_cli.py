"""Integration tests for the CLI."""

from pathlib import Path

from typer.testing import CliRunner

from app.cli.main import app as cli_app

runner = CliRunner()


def test_dataset_build():
    result = runner.invoke(cli_app, ["dataset", "build"])
    assert result.exit_code == 0
    assert "Build OK" in result.stdout


def test_dataset_validate_good(tmp_path):
    # build first so the canonical file exists
    runner.invoke(cli_app, ["dataset", "build"])
    path = Path("benchmark/data/v1.0.0/examples.jsonl")
    result = runner.invoke(cli_app, ["dataset", "validate", str(path)])
    assert result.exit_code == 0
    assert "errors: 0" in result.stdout


def test_dataset_validate_bad_file(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"id": "TEB-X"}\n', encoding="utf-8")  # missing required fields
    result = runner.invoke(cli_app, ["dataset", "validate", str(bad)])
    assert result.exit_code != 0


def test_doctor():
    result = runner.invoke(cli_app, ["doctor"])
    assert result.exit_code == 0
    assert "database: OK" in result.stdout


def test_providers_list():
    result = runner.invoke(cli_app, ["providers", "list"])
    assert result.exit_code == 0
    assert "mock" in result.stdout


def test_version():
    result = runner.invoke(cli_app, ["version"])
    assert result.exit_code == 0
    assert "TEB" in result.stdout
