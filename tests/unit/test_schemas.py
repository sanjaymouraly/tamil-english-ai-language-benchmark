"""Unit tests for core schemas."""

from app.core.schemas import BenchmarkExample, Category, Difficulty
from tests.conftest import make_example


def test_example_roundtrip():
    ex = make_example()
    data = ex.model_dump(mode="json")
    again = BenchmarkExample.model_validate(data)
    assert again.id == ex.id
    assert again.content_hash() == ex.content_hash()


def test_invalid_id_rejected():
    ex = make_example()
    ex.id = "not-prefixed"
    try:
        ex.model_validate(ex.model_dump())
        raise AssertionError("should have rejected bad id")
    except Exception:
        pass


def test_at_least_one_reference_required():
    ex = make_example()
    ex.references = []
    try:
        ex.model_validate(ex.model_dump())
        raise AssertionError("should have rejected empty references")
    except Exception:
        pass


def test_constraint_alternatives_property():
    from app.core.schemas import ConstraintKind, CriticalConstraint

    c = CriticalConstraint(kind=ConstraintKind.MUST_CONTAIN, value=["a", "b"])
    assert c.alternatives == ["a", "b"]
    c2 = CriticalConstraint(kind=ConstraintKind.MUST_CONTAIN, value="x")
    assert c2.alternatives == ["x"]


def test_category_enum_has_16_categories():
    assert len(Category) == 16


def test_difficulty_enum():
    assert {d.value for d in Difficulty} == {"easy", "medium", "hard"}
