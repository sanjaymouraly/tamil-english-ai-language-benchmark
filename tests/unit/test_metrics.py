"""Unit tests for text metrics and utilities."""

from app.core.security import script_kind
from app.evaluation import metrics
from app.evaluation.text_utils import (
    best_reference_similarity,
    char_ngrams,
    edit_similarity,
    extract_numbers,
    jaccard,
    tamil_ratio,
    token_f1,
)
from tests.conftest import make_example


def test_tamil_ratio():
    assert tamil_ratio("நான் போகிறேன்") > 0.9
    assert tamil_ratio("hello world") == 0.0
    assert 0 < tamil_ratio("நான் hello") < 1


def test_script_kind():
    assert script_kind("நான் போகிறேன்") == "tamil"
    assert script_kind("hello world") == "latin"
    assert script_kind("நான் hello") == "mixed"


def test_jaccard_identical():
    a = char_ngrams("நான் போகிறேன்")
    assert jaccard(a, a) == 1.0


def test_token_f1_identical():
    assert token_f1("the cat sat", "the cat sat") == 1.0


def test_token_f1_different():
    assert token_f1("the cat", "dog runs") == 0.0


def test_best_reference_similarity_perfect():
    ex = make_example(references=["I am going to school."])
    sim = best_reference_similarity("I am going to school.", ex.references)
    assert sim > 0.9


def test_edit_similarity_identical():
    assert edit_similarity("hello", "hello") == 1.0


def test_edit_similarity_different():
    assert edit_similarity("abc", "xyz") < 0.5


def test_extract_numbers():
    assert "8" in extract_numbers("at 8 o'clock")
    assert "500000" in extract_numbers("₹5,00,000")


def test_script_validity_tamil_target():
    ex = make_example(target_language="ta")
    result = metrics.script_validity_score(ex, "நான் போகிறேன்.")
    assert result.score == 1.0


def test_script_validity_wrong_script():
    ex = make_example(target_language="ta")
    result = metrics.script_validity_score(ex, "I am going to school.")
    assert result.score == 0.0


def test_fluency_heuristics_clean():
    score, evidence = metrics.fluency_heuristics("This is a clean sentence.")
    assert score == 1.0
    assert evidence == []


def test_fluency_heuristics_repetition():
    score, evidence = metrics.fluency_heuristics("the the the the cat")
    assert score < 1.0
    assert any("repeated" in e for e in evidence)


def test_transliteration_score():
    ex = make_example(
        category="romanized_transliteration",
        source_text="naan pazham saapduven",
        references=["நான் பழம் சாப்பிடுவேன். (I will eat a fruit.)"],
        direction="roman-ta->ta+en",
    )
    score, detail = metrics.transliteration_score(ex, "நான் பழம் சாப்பிடுவேன்.")
    assert score >= 0.5  # script present
    assert detail["tamil_script_present"] is True
