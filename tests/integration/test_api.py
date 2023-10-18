"""Integration tests for the FastAPI application."""

from fastapi.testclient import TestClient

from app.api.main import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_examples_requires_dataset(db_session):
    from app.database import crud
    from tests.conftest import make_example

    crud.upsert_dataset(db_session, [make_example()], version="1.0.0")
    db_session.commit()
    client = TestClient(app)
    response = client.get("/examples?limit=10")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_get_single_example(db_session):
    from app.database import crud
    from tests.conftest import make_example

    ex = make_example()
    crud.upsert_dataset(db_session, [ex], version="1.0.0")
    db_session.commit()
    client = TestClient(app)
    response = client.get(f"/examples/{ex.id}")
    assert response.status_code == 200
    assert response.json()["id"] == ex.id


def test_get_missing_example_404():
    client = TestClient(app)
    response = client.get("/examples/TEB-NOPE-9999")
    assert response.status_code == 404


def test_invalid_job_provider_rejected():
    client = TestClient(app)
    response = client.post("/jobs", json={"name": "x", "provider": "nonexistent"})
    assert response.status_code == 400


def test_providers_list():
    client = TestClient(app)
    response = client.get("/providers")
    assert response.status_code == 200
    data = response.json()
    assert "mock" in data


def test_provider_test_mock():
    client = TestClient(app)
    response = client.post("/providers/test", json={"provider": "mock"})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_response_import_validation():
    client = TestClient(app)
    response = client.post(
        "/responses/import", json={"model_id": "m", "responses": [{"example_id": "E1"}]}
    )
    assert response.status_code == 400  # missing response_text


def test_compare_requires_valid_ids():
    client = TestClient(app)
    response = client.get("/compare?job_ids=abc")
    assert response.status_code == 400


def test_report_unsupported_format():
    client = TestClient(app)
    response = client.post("/jobs/999/report", json={"format": "xml"})
    assert response.status_code == 422  # pydantic validation
