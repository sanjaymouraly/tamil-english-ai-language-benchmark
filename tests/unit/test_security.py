"""Unit tests for security helpers."""

from app.core.logging import mask_secret, redact_text
from app.core.security import looks_like_pii, safe_filename, validate_data_file


def test_safe_filename_strips_traversal():
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("normal.csv") == "normal.csv"


def test_safe_filename_rejects_empty():
    import pytest

    with pytest.raises(ValueError):
        safe_filename("")


def test_mask_secret():
    assert mask_secret("") == ""
    assert mask_secret("sk-1234567890") == "sk-...***"
    assert mask_secret("abc") == "***"


def test_redact_text_masks_api_key():
    redacted = redact_text("api_key=sk-supersecret1234567890")
    assert "sk-supersecret" not in redacted
    assert "REDACTED" in redacted


def test_redact_text_masks_bearer():
    redacted = redact_text("Authorization: Bearer abcdefghijklmnop")
    assert "abcdefghijklmnop" not in redacted


def test_pii_detection_email():
    assert looks_like_pii("contact me at test@example.com")


def test_pii_detection_long_digits():
    assert looks_like_pii("number 1234567890123")


def test_validate_data_file_extension():
    from pathlib import Path

    import pytest

    with pytest.raises(ValueError):
        validate_data_file(Path("evil.exe"))


def test_validate_data_file_missing_ok():
    from pathlib import Path

    validate_data_file(Path("does_not_exist.jsonl"))  # no raise for missing file
