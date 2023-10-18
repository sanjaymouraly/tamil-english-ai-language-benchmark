"""Import/export round-trip tests."""

from app.datasets.loader import dataset_content_hash, export_examples, load_examples
from tests.conftest import make_example, write_jsonl


def test_jsonl_roundtrip(tmp_path):
    examples = [make_example(id=f"TEB-TST-{i:04d}") for i in range(3)]
    path = tmp_path / "examples.jsonl"
    write_jsonl(path, examples)
    loaded = load_examples(path)
    assert len(loaded) == 3
    assert loaded[0].id == examples[0].id
    assert dataset_content_hash(loaded) == dataset_content_hash(examples)


def test_json_roundtrip(tmp_path):
    examples = [make_example()]
    path = tmp_path / "examples.json"
    export_examples(examples, path)
    loaded = load_examples(path)
    assert len(loaded) == 1
    assert loaded[0].source_text == examples[0].source_text


def test_csv_roundtrip(tmp_path):
    examples = [make_example()]
    path = tmp_path / "examples.csv"
    export_examples(examples, path)
    loaded = load_examples(path)
    assert len(loaded) == 1
    assert loaded[0].id == examples[0].id


def test_parquet_roundtrip(tmp_path):
    examples = [make_example()]
    path = tmp_path / "examples.parquet"
    export_examples(examples, path)
    loaded = load_examples(path)
    assert len(loaded) == 1
    assert loaded[0].source_text == examples[0].source_text


def test_unicode_preserved_through_roundtrip(tmp_path):
    ex = make_example(source_text="நான் பள்ளிக்குப் போகிறேன்.")
    path = tmp_path / "examples.jsonl"
    write_jsonl(path, [ex])
    loaded = load_examples(path)
    assert loaded[0].source_text == "நான் பள்ளிக்குப் போகிறேன்."
    # NFC normalization preserved
    import unicodedata

    assert unicodedata.normalize("NFC", loaded[0].source_text) == loaded[0].source_text


def test_invalid_jsonl_raises(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("{not json}\n", encoding="utf-8")
    try:
        load_examples(path)
        raise AssertionError("should have raised")
    except ValueError:
        pass


def test_unsupported_extension(tmp_path):
    path = tmp_path / "examples.txt"
    path.write_text("x", encoding="utf-8")
    try:
        load_examples(path)
        raise AssertionError("should have raised")
    except ValueError:
        pass


def test_register_preserved_through_all_formats(tmp_path):
    """Regression: the `register` field must survive export -> load.

    Exports write the field name ``register_level`` while seed files author the
    alias ``register``. Without ``populate_by_name`` the value was silently
    reset to the ``neutral`` default on every round-trip.
    """
    ex = make_example(register="formal")
    assert ex.register_level.value == "formal"
    for suffix in (".jsonl", ".json", ".csv", ".parquet"):
        path = tmp_path / f"examples{suffix}"
        export_examples([ex], path)
        loaded = load_examples(path)
        assert loaded[0].register_level.value == "formal", f"register lost for {suffix}"


def test_all_fields_survive_jsonl_roundtrip(tmp_path):
    """The full record (glossary, constraints, phenomena, partition) round-trips."""
    ex = make_example(
        glossary=[{"term": "சென்னை", "translation": "Chennai", "language": "ta"}],
        critical_constraints=[{"kind": "must_contain", "value": ["school", "School"]}],
        phenomena=["negation"],
        partition="test",
        register="informal",
    )
    path = tmp_path / "examples.jsonl"
    export_examples([ex], path)
    loaded = load_examples(path)[0]
    assert loaded.model_dump(mode="json") == ex.model_dump(mode="json")
    assert dataset_content_hash([loaded]) == dataset_content_hash([ex])
