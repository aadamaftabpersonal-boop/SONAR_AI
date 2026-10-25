from datetime import UTC, datetime

import pytest
from alembic import command
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.db.models import Business, BusinessResponse
from tests.conftest import TEST_URL, alembic_config
from tests.factories import make_attempt, make_business, make_job

pytestmark = pytest.mark.integration

TABLES = {
    "businesses",
    "search_jobs",
    "call_attempts",
    "provider_events",
    "business_responses",
    "audit_events",
}


def test_migration_round_trip(engine, session):
    cfg = alembic_config(TEST_URL)
    command.downgrade(cfg, "base")
    assert not TABLES & set(inspect(engine).get_table_names())
    command.upgrade(cfg, "head")
    assert TABLES <= set(inspect(engine).get_table_names())


def test_consented_business_requires_consent_timestamp(session):
    session.add(
        Business(
            name="x",
            phone_e164="+910000000099",
            category="pharmacy",
            kind="REAL_BUSINESS",
            source="test",
            participation_status="CONSENTED",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()


def test_invited_business_needs_no_consent_timestamp(session):
    b = make_business(session, participation_status="INVITED", consent_recorded_at=None)
    assert b.id is not None


@pytest.mark.parametrize("bad", ["12345", "+0123456789", "9876543210", "+91 98765 43210"])
def test_phone_must_be_e164(session, bad):
    with pytest.raises(IntegrityError):
        make_business(session, phone_e164=bad)


def test_phone_is_unique(session):
    make_business(session, phone_e164="+910000011111")
    with pytest.raises(IntegrityError):
        make_business(session, phone_e164="+910000011111")


def test_invalid_enum_text_is_rejected(session):
    with pytest.raises(IntegrityError):
        make_business(session, kind="SECRET_AGENT")


def test_duplicate_attempt_slot_rejected(session):
    job, biz = make_job(session), make_business(session)
    make_attempt(session, job, biz)
    with pytest.raises(IntegrityError):
        make_attempt(session, job, biz)


def test_attempt_numbers_can_differ(session):
    job, biz = make_job(session), make_business(session)
    make_attempt(session, job, biz, attempt_number=1)
    make_attempt(session, job, biz, attempt_number=2)


def test_duplicate_provider_call_id_rejected(session):
    job, b1, b2 = make_job(session), make_business(session), make_business(session)
    make_attempt(session, job, b1, provider_call_id="exec-1")
    with pytest.raises(IntegrityError):
        make_attempt(session, job, b2, provider_call_id="exec-1")


def test_invalid_call_status_rejected(session):
    job, biz = make_job(session), make_business(session)
    with pytest.raises(IntegrityError):
        make_attempt(session, job, biz, status="MAYBE")


def test_job_radius_bounds(session):
    with pytest.raises(IntegrityError):
        make_job(session, radius_km=26)


def _response(attempt, job, biz, **over):
    fields = {
        "call_attempt_id": attempt.id,
        "search_job_id": job.id,
        "business_id": biz.id,
        "data_origin": "SIMULATED",
        "availability": "REPORTED_AVAILABLE",
        "exact_match": "CONFIRMED",
        "answer_summary": "x",
        "extraction_status": "VALID",
        "answer_timestamp": datetime.now(UTC),
    }
    fields.update(over)
    return BusinessResponse(**fields)


def test_second_response_for_one_attempt_rejected(session):
    job, biz = make_job(session), make_business(session)
    att = make_attempt(session, job, biz)
    session.add(_response(att, job, biz))
    session.commit()
    session.add(_response(att, job, biz))
    with pytest.raises(IntegrityError):
        session.commit()


def test_response_origin_cannot_be_cached_in_db(session):
    """CACHED_LIVE is derived at read time, never stored (Bible 19.2 notes)."""
    job, biz = make_job(session), make_business(session)
    att = make_attempt(session, job, biz)
    session.add(_response(att, job, biz, data_origin="CACHED_LIVE"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_response_availability_enum_enforced(session):
    job, biz = make_job(session), make_business(session)
    att = make_attempt(session, job, biz)
    session.add(_response(att, job, biz, availability="NO_ANSWER"))
    with pytest.raises(IntegrityError):
        session.commit()
