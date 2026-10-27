"""GET /api/searches/{id}/live: the live transcript ticker (Bible 51 tier T-1, T15.1).

Behind FEATURE_LIVE_TICKER. Shows only calls in progress, only for team test lines and simulated
calls, only text the provider has transcribed so far (never invented), masked and length-capped.
A provider pull happens at most once every LIVE_MIN_PULL_SECONDS per call, however many viewers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_providers, get_session_factory
from app.api.errors import ApiError
from app.config import Settings, get_settings
from app.db.models import Business, CallAttempt, SearchJob
from app.domain.enums import CallStatus, ErrorClass
from app.providers.base import ProviderError
from app.providers.registry import ProviderRegistry
from app.services.live import LiveCache, may_show, ticker_lines

router = APIRouter(prefix="/api")

LIVE_STATUSES = {CallStatus.IN_PROGRESS, CallStatus.PROCESSING}


class TickerLine(BaseModel):
    speaker: str
    text: str


class LiveCall(BaseModel):
    attempt_id: uuid.UUID
    business_id: uuid.UUID
    business_name: str
    status: CallStatus
    lines: list[TickerLine]
    reason: str | None = None  # "no_live_text" | "not_shown" | "provider_unavailable"
    updated_at: datetime


class LiveView(BaseModel):
    search_id: uuid.UUID
    calls: list[LiveCall]


def _cache(request: Request, settings: Settings) -> LiveCache:
    cache = getattr(request.app.state, "live_cache", None)
    if cache is None:
        cache = LiveCache(min_interval=settings.live_min_pull_seconds)
        request.app.state.live_cache = cache
    return cache


async def _transcript(provider, call_id: str) -> str | None:
    if hasattr(provider, "live_transcript"):  # the simulator reveals its script line by line
        return await provider.live_transcript(call_id)
    record = await provider.get_call(call_id)
    return record.transcript


@router.get("/searches/{search_id}/live", response_model=LiveView)
async def live(
    search_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    providers: ProviderRegistry = Depends(get_providers),
) -> LiveView:
    if not settings.feature_live_ticker:
        raise ApiError(404, ErrorClass.NOT_FOUND, "Not found")
    try:
        job_id = uuid.UUID(search_id)
    except ValueError:
        raise ApiError(404, ErrorClass.NOT_FOUND, "Search not found") from None

    with session_factory() as s:
        if s.get(SearchJob, job_id) is None:
            raise ApiError(404, ErrorClass.NOT_FOUND, "Search not found")
        rows = s.execute(
            select(CallAttempt, Business)
            .join(Business, Business.id == CallAttempt.business_id)
            .where(
                CallAttempt.search_job_id == job_id,
                CallAttempt.status.in_([str(st) for st in LIVE_STATUSES]),
            )
            .order_by(CallAttempt.created_at)
        ).all()
        snapshot = [
            (a.id, a.business_id, b.name, b.kind, a.provider, a.provider_call_id, a.status)
            for a, b in rows
        ]

    cache = _cache(request, settings)
    calls: list[LiveCall] = []
    for attempt_id, business_id, name, kind, provider_name, call_id, status in snapshot:
        lines: list[dict] = []
        reason: str | None = None
        if not may_show(kind, provider_name):
            reason = "not_shown"
        elif not call_id or not providers.has(provider_name):
            reason = "no_live_text"
        else:
            hit, transcript = cache.lookup(call_id)
            if not hit:
                try:
                    transcript = await _transcript(providers.get(provider_name), call_id)
                except ProviderError:
                    transcript = None
                    reason = "provider_unavailable"
                cache.store(call_id, transcript)
            lines = ticker_lines(transcript, settings.live_ticker_lines)
            if not lines and reason is None:
                reason = "no_live_text"
        calls.append(
            LiveCall(
                attempt_id=attempt_id,
                business_id=business_id,
                business_name=name,
                status=CallStatus(status),
                lines=[TickerLine(**line) for line in lines],
                reason=reason,
                updated_at=datetime.now(UTC),
            )
        )
    return LiveView(search_id=job_id, calls=calls)
