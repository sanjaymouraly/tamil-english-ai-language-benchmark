"""Unit tests for semantic preservation scoring."""

from app.evaluation.semantic import completeness_score, semantic_preservation_score
from tests.conftest import make_example


def test_perfect_response_scores_one():
    ex = make_example(
        critical_constraints=[{"kind": "must_contain", "value": "school"}],
    )
    result = semantic_preservation_score(ex, "I am going to school.")
    assert result.score is not None
    assert result.score >= 0.9


def test_empty_response_scores_low():
    ex = make_example()
    result = semantic_preservation_score(ex, "")
    assert result.score is not None
    assert result.score < 0.4


def test_missing_constraint_reduces_score():
    ex = make_example(
        critical_constraints=[{"kind": "must_contain", "value": "elephant"}],
    )
    good = semantic_preservation_score(ex, "I am going to school with an elephant.")
    bad = semantic_preservation_score(ex, "I am going to school.")
    assert good.score > bad.score


def test_completeness_empty_is_zero():
    ex = make_example()
    assert completeness_score(ex, "") == 0.0


def test_completeness_reasonable_is_one():
    ex = make_example()
    assert completeness_score(ex, "I am going to school today morning.") == 1.0


def test_components_are_exposed():
    ex = make_example()
    result = semantic_preservation_score(ex, "I am going to school.")
    assert "constraint_satisfaction" in result.components
    assert "reference_overlap" in result.components
    assert result.method == "deterministic_proxy"
