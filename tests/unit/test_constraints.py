"""Unit tests for deterministic constraint checking."""

from app.evaluation.constraints import (
    check_all_constraints,
    constraint_score,
    numeric_preservation_score,
)
from tests.conftest import make_example


def test_must_contain_pass():
    ex = make_example(critical_constraints=[{"kind": "must_contain", "value": "school"}])
    score, checks = constraint_score(ex, "I go to school.")
    assert score == 1.0
    assert all(c.passed for c in checks)


def test_must_contain_fail():
    ex = make_example(critical_constraints=[{"kind": "must_contain", "value": "school"}])
    score, checks = constraint_score(ex, "I go home.")
    assert score == 0.0


def test_must_contain_alternatives():
    ex = make_example(
        critical_constraints=[{"kind": "must_contain", "value": ["Chennai", "சென்னை"]}]
    )
    _, checks = constraint_score(ex, "He works in Chennai.")
    assert checks[0].passed


def test_must_not_contain():
    ex = make_example(critical_constraints=[{"kind": "must_not_contain", "value": "not"}])
    _, checks = constraint_score(ex, "We are going.")
    assert checks[0].passed
    _, checks = constraint_score(ex, "We are not going.")
    assert not checks[0].passed


def test_regex_constraint():
    ex = make_example(critical_constraints=[{"kind": "regex", "value": r"^\d+\."}])
    _, checks = constraint_score(ex, "1. first item")
    assert checks[0].passed


def test_numeric_preservation():
    ex = make_example()
    score, detail = numeric_preservation_score(ex, "I am going to school at 8 o'clock.")
    # source has no numbers, so score is 1.0
    assert score == 1.0


def test_numeric_preservation_missing():
    ex = make_example(source_text="காலை 8 மணிக்கு போகிறேன்.")
    score, detail = numeric_preservation_score(ex, "I am going in the morning.")
    assert score == 0.0
    assert detail["missing"] == ["8"]


def test_entity_preservation():
    ex = make_example(critical_constraints=[{"kind": "entity_preservation", "value": "Chennai"}])
    checks = check_all_constraints(ex, "He works in Chennai.")
    assert checks[0].passed
    checks = check_all_constraints(ex, "He works in Mumbai.")
    assert not checks[0].passed
