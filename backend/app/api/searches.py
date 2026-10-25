"""Search endpoints (Bible 20.2-20.5). Creating a search plans and stores the work; it never
blocks on calls. Dialing is the orchestrator's job (Phase 4)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_providers, rate_limit_search, require_access_key
from app.api.errors import ApiError
from app.config import Settings, get_settings
from app.db.models import Business, BusinessResponse, CallAttempt, SearchJob
from app.db.repositories import AttemptRepo, AuditRepo, SearchRepo, StatsRepo
from app.db.session import get_session
from app.domain.enums import (
    Availability,
    CallStatus,
    DataOrigin,
    ErrorClass,
    ResultState,
    SearchMode,
    SearchStatus,
)
from app.domain.schemas import (
    AttemptView,
    BusinessRef,
    Clarification,
    Counts,
    HistoryView,
    QueryValidationError,
    Refusal,
    ResultsView,
    SearchCreated,
    SearchRequest,
    SearchView,
)
from app.domain.transitions import is_terminal
from app.providers.registry import ProviderRegistry
from app.services import selector
from app.services.categories import get_categories
from app.services.directory import load_candidates
from app.services.geo import bearing_deg, distance_km
from app.services.planning import PlannedCall, plan_order
from app.services.query import parse
from app.services.result_copy import RANKING_EXPLANATION, RETRYING_NOTE
from app.services.results import (
    derive_result_state,
    sort_results,
    view_from_response,
    view_without_response,
)

router = APIRouter(prefix="/api")

TERMINAL_JOB = {
    SearchStatus.COMPLETED,
    SearchStatus.COMPLETED_PARTIAL,
    SearchStatus.FAILED,
    SearchStatus.CANCELLED,
}


def _ttl(settings: Settings) -> dict[str, timedelta]:
    return {
        "availability": timedelta(minutes=settings.freshness_ttl_availability_minutes),
        "price": timedelta(minutes=settings.freshness_ttl_price_minutes),
    }


def _job_or_404(session: Session, search_id: str) -> SearchJob:
    try:
        job_id = uuid.UUID(search_id)
    except ValueError:
        job_id = None
    job = SearchRepo(session).get(job_id) if job_id else None
    if job is None:
        raise ApiError(404, ErrorClass.NOT_FOUND, "Search not found")
    return job


def _require_live_calling(payload: SearchRequest, providers: ProviderRegistry) -> None:
    """A live search must never be planned if it can never be dialed."""
    if payload.demo_mode:
        return
    unavailable = "Live calling is not configured on this server. Use demo mode."
    if not providers.has("bolna"):
        raise ApiError(503, ErrorClass.PROVIDER_UNAVAILABLE, unavailable)
    has_agent = getattr(providers.get("bolna"), "has_agent", None)
    if has_agent is not None and not has_agent(payload.category):
        raise ApiError(
            503,
            ErrorClass.PROVIDER_UNAVAILABLE,
            f"No voice agent is configured for '{payload.category}'. Use demo mode.",
        )


@router.post(
    "/searches",
    status_code=202,
    response_model=SearchCreated,
    dependencies=[Depends(require_access_key), Depends(rate_limit_search)],
)
def create_search(
    payload: SearchRequest,
    response: Response,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    clock: Callable[[], datetime] = Depends(get_clock),
    providers: ProviderRegistry = Depends(get_providers),
) -> SearchCreated:
    try:
        parsed = parse(payload, get_categories())
    except QueryValidationError as exc:
        raise ApiError(422, ErrorClass.VALIDATION, exc.message, exc.field) from exc
    if isinstance(parsed, Refusal):
        raise ApiError(422, ErrorClass.UNSUPPORTED_QUERY, parsed.message)
    _require_live_calling(payload, providers)

    jobs = SearchRepo(session)
    now = clock()

    if isinstance(parsed, Clarification):
        job = jobs.create(
            query_text=payload.query_text,
            category=payload.category,
            status=SearchStatus.NEEDS_CLARIFICATION,
            demo_mode=payload.demo_mode,
            clarification=parsed.model_dump(mode="json"),
        )
        session.commit()
        response.status_code = 200
        return SearchCreated(
            search_id=job.id, status=SearchStatus.NEEDS_CLARIFICATION, clarification=parsed
        )

    candidates = load_candidates(session, parsed.category, now)
    selection = selector.select(
        candidates,
        lat=parsed.lat,
        lng=parsed.lng,
        radius_km=parsed.radius_km,
        now=now,
        max_targets=settings.max_targets_per_search,
        daily_cap=settings.business_daily_call_cap,
        cooldown_minutes=settings.business_cooldown_minutes,
    )
    common = {
        "query_text": parsed.query_text,
        "parsed_query": parsed.model_dump(mode="json"),
        "category": parsed.category,
        "center_lat": parsed.lat,
        "center_lng": parsed.lng,
        "radius_km": parsed.radius_km,
        "demo_mode": parsed.demo_mode,
        "force_fresh": parsed.force_fresh,
    }

    if not selection.targets:
        reasons = ", ".join(f"{n} {why.replace('_', ' ')}" for why, n in selection.excluded.items())
        message = (
            f"No consenting businesses are available to call for this search "
            f"({selection.considered} considered{': ' + reasons if reasons else ''})."
        )
        job = jobs.create(
            **common,
            status=SearchStatus.FAILED,
            error_code=ErrorClass.NO_ELIGIBLE_BUSINESSES,
            error_summary=message,
            completed_at=now,
        )
        session.commit()
        response.status_code = 200
        return SearchCreated(
            search_id=job.id,
            status=SearchStatus.FAILED,
            error_code=ErrorClass.NO_ELIGIBLE_BUSINESSES,
            message=message,
        )

    fast = settings.feature_stop_rule and parsed.mode == SearchMode.FAST
    job = jobs.create(
        **common,
        status=SearchStatus.CREATED,
        planned_targets=len(selection.targets),
        deadline_at=now + timedelta(seconds=settings.search_deadline_seconds),
        mode=parsed.mode,
        stop_rule={"k": settings.stop_rule_k} if fast else None,
    )
    provider = "simulated" if parsed.demo_mode else "bolna"
    attempts = AttemptRepo(session)
    # Without Wave 2 (or in THOROUGH mode) calls go in the order planned; with it, the shops most
    # likely to give a useful answer are called first so a search can stop early.
    plan = (
        plan_order(session, selection.targets, parsed, settings, now)
        if fast
        else [PlannedCall(t, None, None) for t in selection.targets]
    )
    for item in plan:
        attempts.insert(
            search_job_id=job.id,
            business_id=item.target.business_id,
            attempt_number=1,
            provider=provider,
            status=CallStatus.PENDING,
            priority_score=item.priority,
            prior_snapshot=item.snapshot,
        )
    AuditRepo(session).add(
        "api", "search_created", search_job_id=job.id, detail={"targets": len(selection.targets)}
    )
    session.commit()
    return SearchCreated(
        search_id=job.id,
        status=SearchStatus.CREATED,
        planned_targets=[p.target for p in plan] if fast else selection.targets,
    )


def _business_ref(job: SearchJob, business: Business) -> BusinessRef:
    dist = bearing = None
    if None not in (job.center_lat, job.center_lng, business.latitude, business.longitude):
        args = (job.center_lat, job.center_lng, business.latitude, business.longitude)
        dist = round(distance_km(*args), 2)
        bearing = round(bearing_deg(*args), 1)
    return BusinessRef(
        id=business.id,
        name=business.name,
        kind=business.kind,
        distance_km=dist,
        bearing_deg=bearing,
        address=business.address,
    )


def _load(session: Session, job: SearchJob):
    rows = session.execute(
        select(CallAttempt, Business)
        .join(Business, Business.id == CallAttempt.business_id)
        .where(CallAttempt.search_job_id == job.id)
        .order_by(CallAttempt.created_at, CallAttempt.attempt_number)
    ).all()
    responses = {
        r.call_attempt_id: r
        for r in session.execute(
            select(BusinessResponse).where(BusinessResponse.search_job_id == job.id)
        ).scalars()
    }
    return rows, responses


def _state_for(attempt: CallAttempt, response: BusinessResponse | None) -> ResultState:
    availability = Availability(response.availability) if response else None
    return derive_result_state(CallStatus(attempt.status), availability, attempt.failure_reason)


def _history_for(
    session: Session, settings: Settings, business: Business, response: BusinessResponse
) -> HistoryView | None:
    """A labelled past-record line. It never appears without a live answer on the card, never for
    simulated answers, and never before there are enough answered calls to mean something."""
    if not settings.feature_history or response.data_origin == "SIMULATED":
        return None
    stats = StatsRepo(session).get(business.id)
    if stats is None or stats.answered < settings.history_min_answered:
        return None
    return HistoryView(answered=stats.answered, reported_available=stats.reported_available)


def _counts(attempts: list[CallAttempt]) -> Counts:
    c = Counts(planned=len(attempts))
    for a in attempts:
        s = CallStatus(a.status)
        if s == CallStatus.PENDING:
            c.pending += 1
        elif s == CallStatus.COMPLETED:
            c.answered += 1
        elif s in {CallStatus.NO_ANSWER, CallStatus.BUSY}:
            c.no_answer += 1
        elif s == CallStatus.CANCELLED:
            c.cancelled += 1
        elif is_terminal(s):
            c.failed += 1
        else:
            c.in_call += 1
    return c


@router.get("/searches/{search_id}", response_model=SearchView)
def get_search(search_id: str, session: Session = Depends(get_session)) -> SearchView:
    job = _job_or_404(session, search_id)
    rows, responses = _load(session, job)
    attempts = [a for a, _ in rows]
    views = [
        AttemptView(
            attempt_id=a.id,
            business=_business_ref(job, b),
            status=CallStatus(a.status),
            attempt_number=a.attempt_number,
            updated_at=a.updated_at,
            result_state=_state_for(a, responses.get(a.id)),
        )
        for a, b in rows
    ]
    error = None
    if job.error_code:
        error = {"code": job.error_code, "message": job.error_summary}
    return SearchView(
        search_id=job.id,
        status=SearchStatus(job.status),
        demo_mode=job.demo_mode,
        mode=SearchMode(job.mode),
        radius_km=float(job.radius_km) if job.radius_km is not None else None,
        center_lat=job.center_lat,
        center_lng=job.center_lng,
        stopped_early=job.stopped_early,
        calls_avoided=job.calls_avoided,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        deadline_at=job.deadline_at,
        counts=_counts(attempts),
        attempts=views,
        error=error,
    )


@router.get("/searches/{search_id}/results", response_model=ResultsView)
def get_results(
    search_id: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> ResultsView:
    job = _job_or_404(session, search_id)
    rows, responses = _load(session, job)
    now = clock()
    ttl = _ttl(settings)

    # one row per business: the latest attempt, which is the one that decides what to show
    latest: dict[uuid.UUID, tuple[CallAttempt, Business]] = {}
    for a, b in rows:
        if b.id not in latest or a.attempt_number > latest[b.id][0].attempt_number:
            latest[b.id] = (a, b)

    items = []
    for attempt, business in latest.values():
        ref = _business_ref(job, business)
        response = responses.get(attempt.id)
        if response is not None:
            view = view_from_response(response, ref, now, ttl)
            view.history = _history_for(session, settings, business, response)
            items.append(view)
        else:
            origin = (
                DataOrigin.SIMULATED if attempt.provider == "simulated" else DataOrigin.LIVE_CALL
            )
            view = view_without_response(_state_for(attempt, None), ref, origin)
            if attempt.attempt_number > 1 and view.result_state == ResultState.PENDING:
                view.note = RETRYING_NOTE  # keep the earlier silence visible while the retry runs
            items.append(view)

    return ResultsView(
        search_id=job.id,
        complete=SearchStatus(job.status) in TERMINAL_JOB,
        ranking_explanation=RANKING_EXPLANATION,
        results=sort_results(items),
    )


@router.post("/searches/{search_id}/cancel", dependencies=[Depends(require_access_key)])
def cancel_search(search_id: str, session: Session = Depends(get_session)) -> dict[str, str]:
    """Idempotent. Stops new dispatches; in-flight calls finish and are recorded (A-12)."""
    job = _job_or_404(session, search_id)
    if SearchStatus(job.status) in TERMINAL_JOB:
        return {"status": job.status}
    repo = AttemptRepo(session)
    for attempt in repo.for_search(job.id):
        if attempt.status == CallStatus.PENDING:
            repo.update_status(attempt.id, CallStatus.CANCELLED, failure_reason="USER_CANCELLED")
    SearchRepo(session).set_status(job.id, SearchStatus.CANCELLED)
    AuditRepo(session).add("api", "search_cancelled", search_job_id=job.id)
    session.commit()
    return {"status": SearchStatus.CANCELLED}
