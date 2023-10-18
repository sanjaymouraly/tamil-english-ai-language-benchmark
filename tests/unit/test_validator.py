"""Unit tests for dataset validation."""

from app.datasets.validator import check_duplicates, validate_examples
from tests.conftest import make_example


def test_valid_example_passes():
    ex = make_example()
    report = validate_examples([ex])
    assert report.ok
    assert report.valid == 1


def test_empty_source_is_error():
    ex = make_example()
    ex.source_text = ""  # bypass pydantic to test the validator rule
    report = validate_examples([ex])
    assert any(e.rule == "completeness" for e in report.errors)


def test_duplicate_id_is_error():
    ex1 = make_example()
    ex2 = make_example()
    report = validate_examples([ex1, ex2])
    assert any(e.rule == "duplicate_id" for e in report.errors)


def test_script_label_mismatch():
    ex = make_example(source_script="tamil", source_text="hello world")
    report = validate_examples([ex])
    assert any(e.rule == "script_label" for e in report.errors)


def test_reference_leakage_warning():
    ex = make_example(references=["நான் பள்ளிக்குப் போகிறேன்."])
    report = validate_examples([ex])
    assert any(w.rule == "reference_leakage" for w in report.warnings)


def test_replacement_char_detected():
    ex = make_example(source_text="bad � text")
    report = validate_examples([ex])
    assert any(e.rule == "unicode_replacement_char" for e in report.errors)


def test_check_duplicates_finds_copy():
    ex1 = make_example(id="TEB-TST-0001")
    ex2 = make_example(id="TEB-TST-0002")  # same source text
    pairs = check_duplicates([ex1, ex2])
    assert ("TEB-TST-0001", "TEB-TST-0002") in pairs


def test_pii_heuristic_flags_phone():
    from app.core.security import looks_like_pii

    findings = looks_like_pii("call 9876543210 now")
    assert findings


def test_pii_heuristic_clean():
    from app.core.security import looks_like_pii

    assert looks_like_pii("நான் பள்ளிக்குப் போகிறேன்.") == []
