"""Apply the stop rule to a running job (Bible 48.2). Called inside the finalizer's transaction,
which already holds the job row lock, so two finishing calls cannot both trigger the stop."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import SearchJob
from app.db.repositories import AttemptRepo, AuditRepo, ResponseRepo, SearchRepo
from app.domain.enums import CallStatus, SearchMode
from app.domain.schemas import ParsedQuery
from app.services.stoprule import STOP_REASON, Confirmation, satisfied


def maybe_stop(session: Session, job: SearchJob, settings: Settings, now: datetime) -> int:
    """Cancel the calls not yet made if enough shops have confirmed. Returns how many."""
    if not settings.feature_stop_rule or job.mode != SearchMode.FAST or job.stopped_early:
        return 0
    parsed = ParsedQuery.model_validate(job.parsed_query)
    k = int((job.stop_rule or {}).get("k", settings.stop_rule_k))
    require_price = "price" in parsed.required_fields

    responses = ResponseRepo(session).for_search(job.id)
    confirmations = [
        Confirmation(
            business_id=str(r.business_id),
            data_origin=r.data_origin,
            availability=r.availability,
            exact_match=r.exact_match,
            evidence_validated=r.evidence_validated,
            price_present=r.price_amount is not None,
        )
        for r in responses
    ]
    if not satisfied(
        confirmations, k=k, require_price=require_price, allow_simulated=job.demo_mode
    ):
        return 0

    attempts = AttemptRepo(session)
    avoided = 0
    for attempt in attempts.for_search(job.id):
        if attempt.status == CallStatus.PENDING:
            attempts.update_status(attempt.id, CallStatus.CANCELLED, failure_reason=STOP_REASON)
            avoided += 1
    if avoided == 0:
        return 0  # nothing was left to skip, so this is not an early stop

    SearchRepo(session).set_status(
        job.id,
        job.status,
        stopped_early=True,
        calls_avoided=avoided,
        stop_rule={"k": k, "require_price": require_price, "stopped_at": now.isoformat()},
    )
    AuditRepo(session).add(
        "system",
        "stop_rule_satisfied",
        search_job_id=job.id,
        detail={"k": k, "calls_avoided": avoided},
    )
    return avoided
