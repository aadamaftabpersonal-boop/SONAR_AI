import threading
from datetime import timedelta

import pytest
from sqlalchemy import text

from app.db.repositories import (
    AttemptRepo,
    AuditRepo,
    BusinessRepo,
    EventRepo,
    ResponseRepo,
    utcnow,
)
from app.domain.enums import CallStatus
from tests.factories import make_attempt, make_business, make_job

pytestmark = pytest.mark.integration


def test_update_status_only_moves_forward(session):
    job, biz = make_job(session), make_business(session)
    att = make_attempt(session, job, biz)
    repo = AttemptRepo(session)
    assert repo.update_status(att.id, CallStatus.RINGING, provider_status="ringing")
    assert not repo.update_status(att.id, CallStatus.DIALING, provider_status="queued")
    session.commit()
    session.refresh(att)
    assert att.status == CallStatus.RINGING
    # the raw provider status is kept even when the transition is ignored
    assert att.provider_status == "queued"


def test_terminal_status_is_never_overwritten(session):
    job, biz = make_job(session), make_business(session)
    att = make_attempt(session, job, biz)
    repo = AttemptRepo(session)
    assert repo.update_status(att.id, CallStatus.NO_ANSWER)
    assert not repo.update_status(att.id, CallStatus.COMPLETED)
    session.commit()
    session.refresh(att)
    assert att.status == CallStatus.NO_ANSWER
    assert att.completed_at is not None


def test_claim_next_marks_dispatching_and_skips_future_attempts(session):
    job, b1, b2 = make_job(session), make_business(session), make_business(session)
    make_attempt(session, job, b1, not_before=utcnow() + timedelta(hours=1))
    due = make_attempt(session, job, b2)
    claimed = AttemptRepo(session).claim_next()
    session.commit()
    assert claimed.id == due.id
    assert claimed.status == CallStatus.DISPATCHING
    assert AttemptRepo(session).claim_next() is None


def test_concurrent_claims_never_share_an_attempt(session, session_factory):
    """Two workers racing for the same queue must receive different rows (D-006)."""
    job = make_job(session)
    for _ in range(6):
        make_attempt(session, job, make_business(session))

    claimed: list = []
    lock = threading.Lock()
    barrier = threading.Barrier(2)

    def worker():
        with session_factory() as s:
            repo = AttemptRepo(s)
            barrier.wait()
            while True:
                a = repo.claim_next()
                s.commit()
                if a is None:
                    return
                with lock:
                    claimed.append(a.id)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(claimed) == 6
    assert len(set(claimed)) == 6


def test_count_active_counts_slots_not_terminals(session):
    job = make_job(session)
    for status in ("DISPATCHING", "RINGING", "IN_PROGRESS", "COMPLETED", "NO_ANSWER", "PENDING"):
        make_attempt(session, job, make_business(session), status=status)
    assert AttemptRepo(session).count_active() == 3


def test_event_insert_is_idempotent(session):
    repo = EventRepo(session)
    kwargs = {
        "provider": "bolna",
        "provider_call_id": "exec-1",
        "provider_status": "completed",
        "payload": {"status": "completed", "execution_id": "exec-1"},
    }
    assert repo.insert_or_ignore(**kwargs) is True
    assert repo.insert_or_ignore(**kwargs) is False
    # a different payload for the same call and status is a distinct event
    assert repo.insert_or_ignore(**{**kwargs, "payload": {"status": "completed", "x": 1}}) is True


def test_fifty_duplicate_deliveries_store_one_row(session):
    repo = EventRepo(session)
    payload = {"status": "ringing", "execution_id": "exec-9"}
    results = [
        repo.insert_or_ignore(
            provider="bolna", provider_call_id="exec-9", provider_status="ringing", payload=payload
        )
        for _ in range(50)
    ]
    assert results.count(True) == 1


def test_orphan_events_attach_by_call_id(session):
    job, biz = make_job(session), make_business(session)
    att = make_attempt(session, job, biz, provider_call_id="exec-2")
    repo = EventRepo(session)
    repo.insert_or_ignore(
        provider="bolna", provider_call_id="exec-2", provider_status="ringing", payload={"a": 1}
    )
    assert len(repo.orphans("bolna")) == 1
    assert repo.attach_orphans("bolna", "exec-2", att.id) == 1
    assert repo.orphans("bolna") == []


def test_response_is_written_exactly_once(session):
    job, biz = make_job(session), make_business(session)
    att = make_attempt(session, job, biz)
    fields = {
        "call_attempt_id": att.id,
        "search_job_id": job.id,
        "business_id": biz.id,
        "data_origin": "SIMULATED",
        "availability": "REPORTED_AVAILABLE",
        "exact_match": "CONFIRMED",
        "answer_summary": "x",
        "extraction_status": "VALID",
        "answer_timestamp": utcnow(),
    }
    repo = ResponseRepo(session)
    assert repo.insert_once(**fields) is True
    assert repo.insert_once(**fields) is False
    assert len(repo.for_search(job.id)) == 1


def test_mark_opt_out_excludes_business(session):
    biz = make_business(session)
    repo = BusinessRepo(session)
    assert biz.id in {b.id for b in repo.callable_in_category("pharmacy")}
    repo.mark_opt_out(biz.id)
    session.commit()
    assert biz.id not in {b.id for b in repo.callable_in_category("pharmacy")}
    session.refresh(biz)
    assert biz.participation_status == "OPTED_OUT"
    assert biz.opted_out_at is not None


def test_invited_and_declined_are_not_callable(session):
    make_business(session, participation_status="INVITED", consent_recorded_at=None)
    make_business(session, participation_status="DECLINED", consent_recorded_at=None)
    assert BusinessRepo(session).callable_in_category("pharmacy") == []


def test_calls_today_and_last_call(session):
    job, biz = make_job(session), make_business(session)
    now = utcnow()
    make_attempt(session, job, biz, attempt_number=1, started_at=now - timedelta(hours=30))
    make_attempt(session, job, biz, attempt_number=2, started_at=now - timedelta(minutes=5))
    repo = AttemptRepo(session)
    assert repo.calls_today(biz.id, now - timedelta(hours=24)) == 1
    assert repo.last_call_at(biz.id) is not None


def test_audit_row_is_written(session):
    AuditRepo(session).add("system", "test_action", detail={"k": "v"})
    session.commit()
    assert session.execute(text("select count(*) from audit_events")).scalar() == 1
