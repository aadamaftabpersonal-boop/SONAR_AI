"""Human review and independent ground-truth checks (Bible 54.1, FR-34, FR-54).

The point is to learn how often a validated answer was actually right. Simulated answers can never
be reviewed into those numbers (they prove nothing about reality).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BusinessResponse, GroundTruthCheck
from app.db.repositories import AuditRepo
from app.domain.enums import GroundTruthOutcome, VerificationStatus

METHODS = ("IN_PERSON", "SECOND_CALL", "OTHER")


class ReviewError(ValueError):
    pass


def _live_response(session: Session, response_id: uuid.UUID) -> BusinessResponse:
    response = session.get(BusinessResponse, response_id)
    if response is None:
        raise ReviewError("no such response")
    if response.data_origin != "LIVE_CALL":
        raise ReviewError("only live answers can be reviewed; simulated ones prove nothing")
    return response


def list_unchecked(session: Session, limit: int = 20) -> list[BusinessResponse]:
    """Live answers nobody has independently checked yet, newest first."""
    checked = select(GroundTruthCheck.response_id)
    return list(
        session.execute(
            select(BusinessResponse)
            .where(BusinessResponse.data_origin == "LIVE_CALL", BusinessResponse.id.not_in(checked))
            .order_by(BusinessResponse.answer_timestamp.desc())
            .limit(limit)
        ).scalars()
    )


def record_ground_truth(
    session: Session,
    response_id: uuid.UUID,
    *,
    checker: str,
    method: str,
    outcome: GroundTruthOutcome,
    note: str | None = None,
) -> GroundTruthCheck:
    response = _live_response(session, response_id)
    if method not in METHODS:
        raise ReviewError(f"method must be one of {', '.join(METHODS)}")
    if not checker.strip():
        raise ReviewError("say who checked")
    existing = session.execute(
        select(GroundTruthCheck).where(
            GroundTruthCheck.response_id == response_id, GroundTruthCheck.checker == checker
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ReviewError("this checker already recorded a check for this answer")
    check = GroundTruthCheck(
        response_id=response_id,
        checker=checker.strip(),
        method=method,
        outcome=outcome.value,
        note=note,
    )
    session.add(check)
    AuditRepo(session).add(
        f"cli:{checker.strip()}",
        "ground_truth_recorded",
        search_job_id=response.search_job_id,
        business_id=response.business_id,
        detail={"outcome": outcome.value, "method": method},
    )
    session.flush()
    return check


def mark_review(session: Session, response_id: uuid.UUID, *, agrees: bool, reviewer: str) -> None:
    """The reviewer read the transcript excerpt and the stored fields: do they match the call?"""
    response = _live_response(session, response_id)
    response.verification_status = (
        VerificationStatus.HUMAN_REVIEWED if agrees else VerificationStatus.CONTRADICTED
    ).value
    AuditRepo(session).add(
        f"cli:{reviewer}",
        "response_reviewed",
        search_job_id=response.search_job_id,
        business_id=response.business_id,
        detail={"agrees": agrees},
    )
    session.flush()
