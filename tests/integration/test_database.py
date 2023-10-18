"""Integration tests for database CRUD and migrations."""

from app.core.schemas import JobConfig
from app.database import crud
from tests.conftest import make_example


def test_dataset_upsert_and_list(db_session):
    ex = make_example()
    dv = crud.upsert_dataset(db_session, [ex], version="1.0.0")
    assert dv.example_count == 1
    rows = crud.list_examples(db_session, dataset_version_id=dv.id)
    assert len(rows) == 1
    assert rows[0].id == ex.id


def test_dataset_roundtrip_preserves_fields(db_session):
    ex = make_example(
        glossary=[{"term": "database", "translation": "தரவுத்தளம்", "language": "en"}],
        critical_constraints=[{"kind": "must_contain", "value": "school"}],
    )
    crud.upsert_dataset(db_session, [ex], version="1.0.0")
    row = crud.get_example(db_session, ex.id)
    assert row.source_text == ex.source_text
    assert row.glossary[0]["translation"] == "தரவுத்தளம்"
    assert row.critical_constraints[0]["kind"] == "must_contain"


def test_job_lifecycle(db_session):
    config = JobConfig()
    job = crud.create_job(
        db_session,
        name="test job",
        dataset_version_id=1,
        provider="mock",
        model_id="teb-mock-v1",
        config_json=config.model_dump(mode="json"),
        status="created",
        total=0,
    )
    job_id = job.id
    crud.update_job(db_session, job_id, status="running", total=10)
    updated = crud.get_job(db_session, job_id)
    assert updated.status == "running"
    assert updated.total == 10


def test_add_and_list_results(db_session):
    ex = make_example()
    dv = crud.upsert_dataset(db_session, [ex], version="1.0.0")
    job = crud.create_job(
        db_session,
        name="j",
        dataset_version_id=dv.id,
        provider="mock",
        model_id="m",
        config_json={},
        status="created",
        total=1,
    )
    crud.add_result(
        db_session,
        {
            "job_id": job.id,
            "example_id": ex.id,
            "model_id": "m",
            "response_text": "answer",
            "scores_json": {"semantic_preservation": {"score": 0.9}},
            "overall_score": 0.9,
            "semantic_preservation": 0.9,
            "terminology_consistency": None,
            "passed": 1,
            "error": None,
            "duration_ms": 5,
        },
    )
    results = crud.results_for_job(db_session, job.id)
    assert len(results) == 1
    assert results[0].overall_score == 0.9


def test_model_response_import(db_session):
    crud.add_model_response(db_session, "TEB-TST-0001", "model-x", "imported response")
    responses = crud.model_responses(db_session, model_id="model-x")
    assert len(responses) == 1
    assert responses[0].response_text == "imported response"


def test_annotation_review_lifecycle(db_session):
    ex = make_example()
    crud.upsert_dataset(db_session, [ex], version="1.0.0")
    review = crud.add_review(
        db_session,
        {
            "example_id": ex.id,
            "reviewer": "alice",
            "semantic_score": 0.9,
            "terminology_score": 0.8,
            "fluency_score": None,
            "adequacy_score": None,
            "cultural_suitability_score": None,
            "agrees_with_machine": True,
            "status": "approved",
            "notes": "looks good",
        },
    )
    assert review.id is not None
    reviews = crud.reviews_for_example(db_session, ex.id)
    assert len(reviews) == 1
    assert reviews[0].reviewer == "alice"


def test_provider_config_upsert(db_session):
    crud.upsert_provider_config(
        db_session, "openai", base_url="https://api.openai.com/v1", model="gpt-4o-mini", enabled=1
    )
    crud.upsert_provider_config(db_session, "openai", model="gpt-4o")  # update
    configs = crud.provider_configs(db_session)
    assert len(configs) == 1
    assert configs[0].model == "gpt-4o"
