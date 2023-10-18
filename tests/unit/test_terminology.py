"""Unit tests for terminology consistency scoring."""

from app.core.schemas import GlossaryTerm
from app.evaluation.terminology import cross_example_consistency, glossary_adherence, term_variants
from tests.conftest import make_example


def _example_with_glossary():
    return make_example(
        source_text="Please back up the database every night.",
        direction="en->ta",
        source_script="latin",
        glossary=[
            GlossaryTerm(term="database", translation="தரவுத்தளம்", language="en"),
            GlossaryTerm(term="backup", translation="காப்பகப்படுத்தல்", language="en"),
        ],
    )


def test_glossary_adherence_perfect():
    ex = _example_with_glossary()
    result = glossary_adherence(ex, "தரவுத்தளத்தை காப்பகப்படுத்துக.")
    assert result.available
    assert result.score == 1.0


def test_glossary_adherence_miss():
    ex = _example_with_glossary()
    result = glossary_adherence(ex, "தரவுத்தளத்தை சேமிக்குக.")  # backup not translated per glossary
    assert result.available
    assert result.score < 1.0
    assert result.evidence


def test_glossary_adherence_no_applicable_terms():
    ex = make_example()  # no glossary
    result = glossary_adherence(ex, "anything")
    assert not result.available
    assert result.score is None


def test_term_variants_include_inflections():
    term = GlossaryTerm(term="database", translation="தரவுத்தளம்", language="en")
    variants = term_variants(term)
    assert "தரவுத்தளம்" in variants
    assert "தரவுத்தள" in variants  # stem


def test_cross_example_consistency_penalizes_variants():
    ex = _example_with_glossary()
    # Same concept rendered with two different APPROVED variants
    # (base form vs stem) -> unstable.
    results = [
        (ex, "தரவுத்தளம் காப்பகப்படுத்தல்.", ex.glossary),
        (ex, "தரவுத்தள காப்பகப்படுத்த.", ex.glossary),
    ]
    report = cross_example_consistency(results)
    assert report["concepts_seen"] >= 1
    assert report["consistency_factor"] < 1.0


def test_cross_example_consistency_stable_when_consistent():
    ex = _example_with_glossary()
    results = [
        (ex, "தரவுத்தளத்தை காப்பகப்படுத்துக.", ex.glossary),
        (ex, "தரவுத்தளத்தை காப்பகப்படுத்துக.", ex.glossary),
    ]
    report = cross_example_consistency(results)
    assert report["consistency_factor"] == 1.0
