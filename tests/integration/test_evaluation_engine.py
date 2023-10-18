"""Integration tests for the evaluation engine."""

from app.evaluation.engine import EvaluationEngine
from tests.conftest import make_example


def test_engine_produces_separate_semantic_and_terminology():
    engine = EvaluationEngine()
    ex = make_example(
        glossary=[{"term": "school", "translation": "பள்ளி", "language": "en"}],
        source_text="I go to school.",
        direction="en->ta",
        target_language="ta",
        references=["நான் பள்ளிக்குப் போகிறேன்."],
    )
    output = engine.evaluate(ex, "நான் பள்ளிக்குப் போகிறேன்.")
    assert output.record.semantic_preservation is not None
    assert output.record.terminology_consistency is not None
    # perfect response
    assert output.record.semantic_preservation >= 0.9
    assert output.record.terminology_consistency == 1.0


def test_engine_flags_empty_response():
    engine = EvaluationEngine()
    ex = make_example()
    output = engine.evaluate(ex, "")
    assert output.record.error is not None
    assert "empty" in output.record.error


def test_engine_composite_is_weighted():
    engine = EvaluationEngine()
    ex = make_example()
    output = engine.evaluate(ex, "I am going to school.")
    assert output.record.overall_score is not None
    assert 0.0 <= output.record.overall_score <= 1.0


def test_engine_unavailable_dimensions_null():
    engine = EvaluationEngine()
    ex = make_example()  # no glossary -> terminology unavailable
    output = engine.evaluate(ex, "I am going to school.")
    assert output.record.terminology_consistency is None
    assert output.record.dimensions["terminology_consistency"].available is False


def test_engine_negation_failure_detected():
    engine = EvaluationEngine()
    ex = make_example(
        critical_constraints=[
            {"kind": "must_contain", "value": "not"},
            {"kind": "must_contain", "value": "school"},
        ],
    )
    output = engine.evaluate(ex, "We are going to school today.")  # drops negation
    assert any("omission" in e for e in output.errors)


def test_engine_transliteration_dimension_for_romanized():
    engine = EvaluationEngine()
    ex = make_example(
        category="romanized_transliteration",
        direction="roman-ta->ta+en",
        source_text="naan pazham saapduven",
        references=["நான் பழம் சாப்பிடுவேன்."],
    )
    output = engine.evaluate(ex, "நான் பழம் சாப்பிடுவேன்.")
    assert "transliteration_accuracy" in output.record.dimensions


def test_engine_judge_callback_used_when_provided():
    from app.core.schemas import DimensionScore

    def fake_judge(dimension, prompt):
        return DimensionScore(
            dimension=dimension,
            score=0.9,
            provenance="llm_judge",
            evidence=["judge evaluated"],
        )

    engine = EvaluationEngine(judge_callback=fake_judge)
    ex = make_example()
    output = engine.evaluate(ex, "I am going to school.")
    assert "adequacy" in output.record.dimensions
    assert output.record.dimensions["adequacy"].provenance == "llm_judge"


def test_engine_deterministic_with_same_input():
    engine = EvaluationEngine()
    ex = make_example()
    r1 = engine.evaluate(ex, "I am going to school.")
    r2 = engine.evaluate(ex, "I am going to school.")
    assert r1.record.semantic_preservation == r2.record.semantic_preservation


def test_passed_is_false_not_none_for_failing_example():
    """Regression: a below-threshold score must yield passed=False.

    A previous `(overall >= threshold) or None` expression turned every
    failing example into passed=None, erasing the pass/fail signal.
    """
    engine = EvaluationEngine()
    ex = make_example()
    output = engine.evaluate(ex, "completely unrelated response")
    assert output.record.overall_score is not None
    if output.record.overall_score < 0.7:
        assert output.record.passed is False
    else:
        assert output.record.passed is True


def test_passed_true_for_good_response():
    engine = EvaluationEngine()
    ex = make_example()
    output = engine.evaluate(ex, "I am going to school.")
    assert output.record.passed is True


def test_instruction_following_unavailable_without_structural_requirement():
    """No invented score: instruction-following is null when unverifiable."""
    engine = EvaluationEngine()
    ex = make_example(category="instruction_following")
    output = engine.evaluate(ex, "I am going to school.")
    dim = output.record.dimensions["instruction_following"]
    assert dim.available is False
    assert dim.score is None


def test_instruction_following_scored_from_regex_requirement():
    engine = EvaluationEngine()
    ex = make_example(
        category="instruction_following",
        critical_constraints=[{"kind": "regex", "value": r"(?m)^\s*[0-9]+[.)]"}],
    )
    good = engine.evaluate(ex, "1. First item\n2. Second item")
    bad = engine.evaluate(ex, "First item and second item")
    assert good.record.dimensions["instruction_following"].score == 1.0
    assert bad.record.dimensions["instruction_following"].score == 0.0
    assert any("structural_error" in e for e in bad.errors)
