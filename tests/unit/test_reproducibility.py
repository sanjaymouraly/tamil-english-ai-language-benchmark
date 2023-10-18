"""Regression tests for dataset build reproducibility.

The content hash identifies a dataset release and must be a deterministic
function of the benchmark *content* only. Ingestion metadata such as
``created_at`` must not affect it, otherwise every rebuild would look like a
new dataset version (the original implementation had exactly this bug).
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.datasets.loader import VOLATILE_FIELDS, canonical_record, dataset_content_hash
from app.datasets.registry import DatasetRegistry
from tests.conftest import make_example


def test_content_hash_ignores_created_at():
    a = make_example()
    b = make_example()
    b.created_at = datetime(1999, 1, 1, tzinfo=UTC)
    assert dataset_content_hash([a]) == dataset_content_hash([b])


def test_content_hash_is_stable_across_calls():
    examples = [make_example(id=f"TEB-TST-{i:04d}") for i in range(1, 6)]
    assert dataset_content_hash(examples) == dataset_content_hash(examples)


def test_content_hash_changes_when_content_changes():
    a = make_example()
    b = make_example(source_text="வேறு வாக்கியம்.")
    assert dataset_content_hash([a]) != dataset_content_hash([b])


def test_canonical_record_drops_only_volatile_fields():
    record = {"id": "TEB-TST-0001", "created_at": "2026-01-01", "source_text": "x"}
    canonical = canonical_record(record)
    assert "created_at" not in canonical
    assert canonical["id"] == "TEB-TST-0001"
    assert {"created_at"} == VOLATILE_FIELDS


def test_registry_register_is_idempotent(tmp_path):
    registry = DatasetRegistry(tmp_path / "registry")
    examples = [make_example()]
    registry.register("TEB", "1.0.0", examples)
    registry.register("TEB", "1.0.0", examples)
    versions = registry.list_versions()
    assert len(versions) == 1
    assert versions[0].version == "1.0.0"


def test_seeded_sampling_is_reproducible_and_bounded():
    from app.core.schemas import JobConfig
    from app.services.evaluation_service import select_examples

    examples = [
        make_example(id=f"TEB-TST-{i:04d}", partition=("train" if i % 2 else "test"))
        for i in range(1, 21)
    ]
    cfg = JobConfig(max_examples=5, sampling_seed=42)
    a = [e.id for e in select_examples(examples, cfg)]
    b = [e.id for e in select_examples(examples, cfg)]
    assert a == b  # same seed -> same sample
    assert len(a) == 5

    cfg_other = JobConfig(max_examples=5, sampling_seed=7)
    c = [e.id for e in select_examples(examples, cfg_other)]
    assert c != a  # different seed -> different sample

    # Partition filter applies before sampling.
    only_test = select_examples(examples, JobConfig(partition="test", max_examples=3))
    assert len(only_test) == 3
    assert all(e.partition == "test" for e in only_test)


def test_seeded_sampling_does_not_exceed_available():
    from app.core.schemas import JobConfig
    from app.services.evaluation_service import select_examples

    examples = [make_example(id="TEB-TST-0001")]
    assert len(select_examples(examples, JobConfig(max_examples=50))) == 1
