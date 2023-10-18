"""Human annotation workflow: independent scoring, disagreement
tracking, and adjudication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import JobStateError
from app.core.schemas import AdjudicationRecord, ReviewRecord
from app.database import crud
from app.database.models import Adjudication, AnnotationReview


@dataclass
class ReviewSummary:
    example_id: str
    review_count: int
    avg_semantic: float | None
    avg_terminology: float | None
    disagreement: bool
    status: str  # pending | approved | disputed
    reviewers: list[str]


def submit_review(session: Session, review: ReviewRecord) -> AnnotationReview:
    """Record one reviewer's independent scores."""
    if not review.reviewer.strip():
        raise JobStateError("reviewer name is required")
    for field_name in (
        "semantic_score",
        "terminology_score",
        "fluency_score",
        "adequacy_score",
        "cultural_suitability_score",
    ):
        value = getattr(review, field_name)
        if value is not None and not (0.0 <= value <= 1.0):
            raise JobStateError(f"{field_name} must be between 0 and 1")
    row = crud.add_review(session, review.model_dump())
    return row


def summarize_reviews(session: Session, example_id: str) -> ReviewSummary:
    rows = crud.reviews_for_example(session, example_id)
    if not rows:
        return ReviewSummary(example_id, 0, None, None, False, "pending", [])

    semantic = [r.semantic_score for r in rows if r.semantic_score is not None]
    terminology = [r.terminology_score for r in rows if r.terminology_score is not None]
    reviewers = [r.reviewer for r in rows]

    disagreement = False
    if len(semantic) >= 2:
        spread = max(semantic) - min(semantic)
        if spread > 0.3:
            disagreement = True
    if len(terminology) >= 2:
        spread = max(terminology) - min(terminology)
        if spread > 0.3:
            disagreement = True
    for r in rows:
        if r.status == "disputed":
            disagreement = True

    approved = all(r.status == "approved" for r in rows) and len(rows) > 0
    status = (
        "approved" if approved and not disagreement else ("disputed" if disagreement else "pending")
    )

    return ReviewSummary(
        example_id=example_id,
        review_count=len(rows),
        avg_semantic=round(sum(semantic) / len(semantic), 4) if semantic else None,
        avg_terminology=round(sum(terminology) / len(terminology), 4) if terminology else None,
        disagreement=disagreement,
        status=status,
        reviewers=reviewers,
    )


def adjudication_summary(session: Session, example_id: str) -> list[dict[str, Any]]:
    return [
        {
            "id": a.id,
            "adjudicator": a.adjudicator,
            "decision": a.decision,
            "final_scores": a.final_scores,
            "notes": a.notes,
            "adjudicated_at": a.adjudicated_at.isoformat() if a.adjudicated_at else None,
        }
        for a in crud.adjudications_for_example(session, example_id)
    ]


# Adjudication decisions that resolve a dispute.
ADJUDICATION_DECISIONS = {"uphold", "override", "revise"}


def submit_adjudication(session: Session, record: AdjudicationRecord) -> Adjudication:
    """Record a final adjudicated decision for a disputed example."""
    if not record.adjudicator.strip():
        raise JobStateError("adjudicator name is required")
    decision = record.decision.strip().lower()
    if decision not in ADJUDICATION_DECISIONS:
        raise JobStateError(f"decision must be one of {sorted(ADJUDICATION_DECISIONS)}")
    for key, value in record.final_scores.items():
        if value is not None and not (0.0 <= value <= 1.0):
            raise JobStateError(f"final score '{key}' must be between 0 and 1")
    payload = record.model_dump()
    payload["decision"] = decision
    return crud.add_adjudication(session, payload)


def example_annotation_status(session: Session, example_id: str) -> dict[str, Any]:
    """Combined human-review state for one example."""
    summary = summarize_reviews(session, example_id)
    return {
        "example_id": example_id,
        "summary": {
            "review_count": summary.review_count,
            "avg_semantic": summary.avg_semantic,
            "avg_terminology": summary.avg_terminology,
            "disagreement": summary.disagreement,
            "status": summary.status,
            "reviewers": summary.reviewers,
        },
        "adjudications": adjudication_summary(session, example_id),
    }


def verification_breakdown(session: Session) -> dict[str, int]:
    """Count examples by verification status."""
    from sqlalchemy import func, select

    from app.database.models import Example

    rows = session.execute(
        select(Example.verification_status, func.count()).group_by(Example.verification_status)
    ).all()
    return {status: count for status, count in rows}
