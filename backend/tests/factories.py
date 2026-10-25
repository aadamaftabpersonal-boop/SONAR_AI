"""Small builders for test rows. Fictional numbers only (+91 00000xxxxx matches no real line)."""

from __future__ import annotations

import itertools
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import Business, CallAttempt, SearchJob

_counter = itertools.count(1)


def make_business(session: Session, **over) -> Business:
    n = next(_counter)
    fields = {
        "name": f"Test Shop {n}",
        "phone_e164": f"+9100000{n:05d}",
        "category": "pharmacy",
        "kind": "TEAM_TEST_LINE",
        "source": "test",
        "participation_status": "TEST_LINE",
        "consent_recorded_at": datetime.now(UTC),
        "latitude": 12.97,
        "longitude": 77.59,
    }
    fields.update(over)
    b = Business(**fields)
    session.add(b)
    session.commit()
    return b


def make_job(session: Session, **over) -> SearchJob:
    fields = {"query_text": "test query", "status": "RUNNING", "category": "pharmacy"}
    fields.update(over)
    j = SearchJob(**fields)
    session.add(j)
    session.commit()
    return j


def make_attempt(session: Session, job: SearchJob, business: Business, **over) -> CallAttempt:
    fields = {
        "search_job_id": job.id,
        "business_id": business.id,
        "attempt_number": 1,
        "provider": "simulated",
        "status": "PENDING",
    }
    fields.update(over)
    a = CallAttempt(**fields)
    session.add(a)
    session.commit()
    return a
