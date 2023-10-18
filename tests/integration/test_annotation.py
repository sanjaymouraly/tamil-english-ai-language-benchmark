"""Integration tests for the human annotation & adjudication workflow."""

from fastapi.testclient import TestClient

from app.annotation.service import (
    submit_adjudication,
    submit_review,
    summarize_reviews,
)
from app.api.main import app
from app.core.errors import JobStateError
from app.core.schemas import AdjudicationRecord, ReviewRecord
from app.database import crud
from tests.conftest import make_example


def _seed(db_session):
    """Insert a fresh example into the DB and return it (committed)."""
    ex = make_example()
    crud.upsert_dataset(db_session, [ex], version="1.0.0")
    db_session.commit()
    return ex


def test_submit_review_and_summarize(db_session):
    ex = _seed(db_session)
    review = ReviewRecord(
        example_id=ex.id,
        reviewer="alice",
        semantic_score=0.9,
        terminology_score=0.8,
        agrees_with_machine=True,
        status="approved",
    )
    row = submit_review(db_session, review)
    assert row.id is not None

    summary = summarize_reviews(db_session, ex.id)
    assert summary.review_count == 1
    assert summary.avg_semantic == 0.9
    assert summary.avg_terminology == 0.8
    assert summary.status == "approved"


def test_review_requires_reviewer(db_session):
    ex = _seed(db_session)
    review = ReviewRecord(example_id=ex.id, reviewer="  ")
    try:
        submit_review(db_session, review)
        raise AssertionError("should have raised")
    except JobStateError:
        pass


def test_review_score_bounds(db_session):
    ex = _seed(db_session)
    review = ReviewRecord(example_id=ex.id, reviewer="bob", semantic_score=1.5)
    try:
        submit_review(db_session, review)
        raise AssertionError("should have raised")
    except JobStateError:
        pass


def test_disagreement_detected(db_session):
    ex = _seed(db_session)
    submit_review(
        db_session,
        ReviewRecord(example_id=ex.id, reviewer="a", semantic_score=0.95, status="approved"),
    )
    submit_review(
        db_session,
        ReviewRecord(example_id=ex.id, reviewer="b", semantic_score=0.5, status="disputed"),
    )
    summary = summarize_reviews(db_session, ex.id)
    assert summary.disagreement is True
    assert summary.status == "disputed"


def test_submit_adjudication(db_session):
    ex = _seed(db_session)
    adj = submit_adjudication(
        db_session,
        AdjudicationRecord(
            example_id=ex.id,
            adjudicator="carol",
            decision="override",
            final_scores={"semantic_preservation": 0.7},
            notes="machine missed context",
        ),
    )
    assert adj.decision == "override"
    assert adj.final_scores == {"semantic_preservation": 0.7}


def test_adjudication_invalid_decision(db_session):
    ex = _seed(db_session)
    try:
        submit_adjudication(
            db_session,
            AdjudicationRecord(example_id=ex.id, adjudicator="carol", decision="banana"),
        )
        raise AssertionError("should have raised")
    except JobStateError:
        pass


def test_adjudication_invalid_score(db_session):
    ex = _seed(db_session)
    try:
        submit_adjudication(
            db_session,
            AdjudicationRecord(
                example_id=ex.id,
                adjudicator="carol",
                decision="uphold",
                final_scores={"semantic_preservation": 2.0},
            ),
        )
        raise AssertionError("should have raised")
    except JobStateError:
        pass


# --- API ---


def test_api_submit_review(db_session):
    ex = _seed(db_session)
    client = TestClient(app)
    response = client.post(
        "/annotations/review",
        json={
            "example_id": ex.id,
            "reviewer": "alice",
            "semantic_score": 0.9,
            "status": "approved",
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_api_submit_review_bad_status(db_session):
    client = TestClient(app)
    response = client.post(
        "/annotations/review",
        json={"example_id": "TEB-T2E-0001", "reviewer": "a", "status": "weird"},
    )
    assert response.status_code == 422


def test_api_adjudicate(db_session):
    ex = _seed(db_session)
    client = TestClient(app)
    response = client.post(
        "/annotations/adjudicate",
        json={
            "example_id": ex.id,
            "adjudicator": "carol",
            "decision": "uphold",
        },
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "uphold"


def test_api_adjudicate_bad_decision(db_session):
    client = TestClient(app)
    response = client.post(
        "/annotations/adjudicate",
        json={"example_id": "TEB-T2E-0001", "adjudicator": "c", "decision": "nope"},
    )
    assert response.status_code == 400


def test_api_annotation_detail(db_session):
    ex = _seed(db_session)
    client = TestClient(app)
    client.post(
        "/annotations/review",
        json={"example_id": ex.id, "reviewer": "a", "semantic_score": 0.8},
    )
    response = client.get(f"/annotations/{ex.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["review_count"] == 1
    assert body["adjudications"] == []
