"""The weekly demand digest for a consenting shop (Bible 49, FR-41, NFR-16).

What a shop gets back for saying yes: how many searches near it asked for what. Privacy rules:
- built from live searches only: demo, simulated and team-test-line-only traffic is excluded
- a line is shown only if at least `min_k` searches contribute; smaller counts are suppressed
- it holds no user identifiers and no free text: only structured item names
Honest limit: Sonar has no user accounts, so the count is of *searches*, not of distinct people.
"""

from __future__ import annotations

import secrets
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Business, BusinessResponse, CallAttempt, SearchJob
from app.db.repositories import AttemptRepo, AuditRepo

WINDOW_DAYS = 7
HONEST_NOTE = (
    "This counts searches, not people. It shows only items searched for at least {k} times, so "
    "smaller counts are hidden. Sonar holds no names or contact details of searchers."
)


@dataclass
class DigestLine:
    item: str
    category: str
    searches: int
    you_reported_available: int


@dataclass
class Digest:
    business_name: str
    window_days: int
    lines: list[DigestLine] = field(default_factory=list)
    suppressed_lines: int = 0
    note: str = ""


def new_token() -> str:
    return secrets.token_urlsafe(32)


def enable_digest(session: Session, business_id: uuid.UUID) -> str:
    """Opt a consenting shop in and return its private link token (kept if it already has one)."""
    business = session.get(Business, business_id)
    if business is None:
        raise ValueError("no such business")
    if business.opted_out_at is not None:
        raise ValueError("this business has opted out")
    if not business.digest_token:
        business.digest_token = new_token()
    business.digest_opt_in = True
    AuditRepo(session).add("cli:digest", "digest_enabled", business_id=business_id)
    session.flush()
    return business.digest_token


def business_for_token(session: Session, token: str) -> Business | None:
    if not token:
        return None
    business = session.execute(
        select(Business).where(Business.digest_token == token)
    ).scalar_one_or_none()
    if business is None or not business.digest_opt_in or business.opted_out_at is not None:
        return None
    return business


def generate(session: Session, business: Business, now: datetime, min_k: int) -> Digest:
    since = now - timedelta(days=WINDOW_DAYS)
    rows = session.execute(
        select(CallAttempt, SearchJob)
        .join(SearchJob, SearchJob.id == CallAttempt.search_job_id)
        .where(
            CallAttempt.business_id == business.id,
            CallAttempt.provider != "simulated",
            SearchJob.demo_mode.is_(False),
            SearchJob.created_at >= since,
            SearchJob.parsed_query.is_not(None),
        )
    ).all()

    searches: dict[tuple[str, str], set[uuid.UUID]] = defaultdict(set)
    for _, job in rows:
        query = job.parsed_query or {}
        item = str(query.get("item_name", "")).strip()
        if item:
            searches[(item.lower(), str(query.get("category", "")))].add(job.id)

    # drop searches whose every target was a team test line: that is us, not demand
    attempts = AttemptRepo(session)
    live_only: dict[tuple[str, str], set[uuid.UUID]] = {}
    for key, job_ids in searches.items():
        real = {
            job_id
            for job_id in job_ids
            if any(
                session.get(Business, a.business_id).kind == "REAL_BUSINESS"
                for a in attempts.for_search(job_id)
            )
        }
        if real:
            live_only[key] = real

    digest = Digest(
        business_name=business.name, window_days=WINDOW_DAYS, note=HONEST_NOTE.format(k=min_k)
    )
    for (item, category), job_ids in sorted(live_only.items(), key=lambda kv: -len(kv[1])):
        if len(job_ids) < min_k:
            digest.suppressed_lines += 1  # counted, never named: the item itself stays hidden
            continue
        yes = session.execute(
            select(BusinessResponse).where(
                BusinessResponse.business_id == business.id,
                BusinessResponse.search_job_id.in_(job_ids),
                BusinessResponse.availability == "REPORTED_AVAILABLE",
                BusinessResponse.data_origin == "LIVE_CALL",
            )
        ).scalars()
        digest.lines.append(
            DigestLine(
                item=item,
                category=category,
                searches=len(job_ids),
                you_reported_available=len(list(yes)),
            )
        )
    return digest
