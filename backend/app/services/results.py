"""Turn attempts and responses into API result views (Bible 6.1, 20.4, 24.3)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

from app.domain.enums import (
    Availability,
    CallStatus,
    DataOrigin,
    ExactMatch,
    Freshness,
    ResultState,
    VerificationStatus,
)
from app.domain.schemas import (
    AnswerView,
    BusinessRef,
    Evidence,
    Reported,
    ReportedPrice,
    ResultView,
)
from app.services.freshness import field_freshness
from app.services.result_copy import NOTES

# Ranking tiers (Bible 24.3, lexicographic, no invented scores: D-016)
TIER: dict[ResultState, int] = {
    ResultState.REPORTED_AVAILABLE: 1,
    ResultState.ALTERNATIVE_ONLY: 3,
    ResultState.UNCERTAIN: 4,
    ResultState.REPORTED_UNAVAILABLE: 5,
    ResultState.DECLINED: 6,
    ResultState.NO_ANSWER: 7,
    ResultState.CALL_FAILED: 7,
    ResultState.PENDING: 7,
    ResultState.CANCELLED: 7,
    ResultState.NOT_CALLED_STOP_RULE: 7,
}

_AVAILABILITY_TO_STATE = {
    Availability.REPORTED_AVAILABLE: ResultState.REPORTED_AVAILABLE,
    Availability.REPORTED_UNAVAILABLE: ResultState.REPORTED_UNAVAILABLE,
    Availability.ALTERNATIVE_ONLY: ResultState.ALTERNATIVE_ONLY,
    Availability.UNCERTAIN: ResultState.UNCERTAIN,
    Availability.DECLINED: ResultState.DECLINED,
}

_IN_FLIGHT = {
    CallStatus.PENDING,
    CallStatus.DISPATCHING,
    CallStatus.DISPATCH_UNKNOWN,
    CallStatus.DIALING,
    CallStatus.RINGING,
    CallStatus.IN_PROGRESS,
    CallStatus.PROCESSING,
}


def derive_result_state(
    call_status: CallStatus,
    availability: Availability | None,
    failure_reason: str | None = None,
) -> ResultState:
    """The one place a state is chosen. No response row means never 'unavailable' (FR-16)."""
    if availability is not None:
        return _AVAILABILITY_TO_STATE[availability]
    if call_status in _IN_FLIGHT:
        return ResultState.PENDING
    if call_status == CallStatus.CANCELLED:
        if failure_reason == "STOP_RULE_SATISFIED":
            return ResultState.NOT_CALLED_STOP_RULE
        return ResultState.CANCELLED
    if call_status in {CallStatus.NO_ANSWER, CallStatus.BUSY}:
        return ResultState.NO_ANSWER
    if call_status == CallStatus.COMPLETED:
        # completed but nothing usable (voicemail, IVR, no human): treated like no answer (V14)
        return ResultState.NO_ANSWER
    # FAILED, ERROR, STOPPED, INSUFFICIENT_BALANCE, TIMED_OUT
    return ResultState.CALL_FAILED


def rank_key(state: ResultState, distance_km: float | None, price: float | None) -> tuple:
    """Within a tier: nearer first, then cheaper (priced before unpriced)."""
    return (
        TIER[state],
        distance_km if distance_km is not None else float("inf"),
        price is None,
        price if price is not None else 0.0,
    )


def freshness_for(response: Any, now: datetime, ttl: dict[str, timedelta]) -> dict[str, Freshness]:
    ts = response.answer_timestamp
    return {
        "availability": field_freshness(True, ts, now, ttl["availability"]),
        "price": field_freshness(response.price_amount is not None, ts, now, ttl["price"]),
    }


def view_from_response(
    response: Any, business: BusinessRef, now: datetime, ttl: dict[str, timedelta]
) -> ResultView:
    state = _AVAILABILITY_TO_STATE[Availability(response.availability)]
    price = None
    if response.price_amount is not None or response.price_note:
        price = ReportedPrice(
            amount=float(response.price_amount) if response.price_amount is not None else None,
            currency=response.price_currency,
            note=response.price_note,
        )
    return ResultView(
        business=business,
        result_state=state,
        data_origin=DataOrigin(response.data_origin),
        answer_timestamp=response.answer_timestamp,
        freshness=freshness_for(response, now, ttl),
        reported=Reported(
            exact_match=ExactMatch(response.exact_match),
            price=price,
            quantity=response.quantity_reported,
            wait_time_minutes=response.wait_time_minutes,
            open_status=response.open_status,
        ),
        answer_summary=response.answer_summary,
        evidence=Evidence(excerpt=response.evidence_excerpt, validated=response.evidence_validated),
        verification_status=VerificationStatus(response.verification_status),
        flags=list(response.validation_flags or []),
        note=NOTES.get(state),
        answers=_answers(response),
        rank_value=_float(getattr(response, "rank_value", None)),
    )


def _float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _answers(response: Any) -> list[AnswerView] | None:
    raw = getattr(response, "answers", None)
    if not raw:
        return None
    return [AnswerView.model_validate(a) for a in raw]


def view_without_response(
    state: ResultState, business: BusinessRef, origin: DataOrigin
) -> ResultView:
    return ResultView(
        business=business,
        result_state=state,
        data_origin=origin,
        reported=None,
        evidence=None,
        note=NOTES.get(state),
    )


def sort_results(items: Iterable[ResultView], rank: str | None = None) -> list[ResultView]:
    """`rank` ("lowest" or "highest") orders shops within a tier by the custom question the user
    chose (D-062); otherwise by price as before."""

    def key(v: ResultView) -> tuple:
        if rank:
            value = v.rank_value
            if value is not None and rank == "highest":
                value = -value
            distance = v.business.distance_km
            # the user's own ordering comes before distance: "cheapest" means cheapest
            return (
                TIER[v.result_state],
                value is None,
                value if value is not None else 0.0,
                distance if distance is not None else float("inf"),
            )
        price = v.reported.price.amount if v.reported and v.reported.price else None
        return rank_key(v.result_state, v.business.distance_km, price)

    return sorted(items, key=key)
