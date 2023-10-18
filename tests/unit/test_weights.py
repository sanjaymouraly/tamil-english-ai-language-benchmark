"""Unit tests for score weights and composite scoring."""

from app.evaluation.weights import ScoreWeights


def test_composite_all_dimensions():
    w = ScoreWeights()
    scores = {"semantic_preservation": 1.0, "terminology_consistency": 1.0}
    assert w.composite(scores) == 1.0


def test_composite_renormalizes_over_available():
    w = ScoreWeights()
    # Only semantic available -> composite == semantic
    scores = {"semantic_preservation": 0.8, "terminology_consistency": None}
    assert w.composite(scores) == 0.8


def test_composite_all_none():
    w = ScoreWeights()
    assert w.composite({"semantic_preservation": None}) is None


def test_composite_weighted():
    w = ScoreWeights(weights={"a": 1.0, "b": 3.0})
    scores = {"a": 1.0, "b": 0.0}
    assert w.composite(scores) == 0.25


def test_negative_weights_rejected():
    try:
        ScoreWeights(weights={"a": -1.0})
        raise AssertionError("should reject negative weights")
    except ValueError:
        pass


def test_default_weights_include_semantic_and_terminology():
    w = ScoreWeights()
    assert "semantic_preservation" in w.weights
    assert "terminology_consistency" in w.weights
