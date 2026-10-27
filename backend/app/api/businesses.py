"""Shops near a point for the map, and OpenStreetMap discovery (D-059, D-060).

`GET /api/businesses/nearby` lists every shop Sonar knows in the radius with its participation
status, so the map can show who has joined and who has not. No phone number ever leaves here.
`POST /api/businesses/discover` (access key, FEATURE_DISCOVERY) looks shops up on OpenStreetMap and
stores new ones as INVITED, which the selector never calls.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import _client_key, get_clock, require_access_key
from app.api.errors import ApiError
from app.config import Settings, get_settings
from app.db.models import Business
from app.db.session import get_session
from app.domain.enums import BusinessKind, ErrorClass, ParticipationStatus, PlanTier
from app.domain.schemas import MAX_RADIUS_KM, MIN_RADIUS_KM
from app.services import osm
from app.services.categories import get_categories
from app.services.discovery import store_discovered
from app.services.geo import bearing_deg, distance_km
from app.services.plans import radius_error
from app.services.selector import CALLABLE

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/businesses")

HIDDEN = {ParticipationStatus.OPTED_OUT, ParticipationStatus.DECLINED}
MAX_LISTED = 200


class NearbyBusiness(BaseModel):
    id: str
    name: str
    kind: BusinessKind
    participation_status: ParticipationStatus
    contactable: bool  # Sonar may call it (joined, not opted out)
    distance_km: float
    bearing_deg: float
    address: str | None = None
    source: str


class NearbyView(BaseModel):
    businesses: list[NearbyBusiness]
    attribution: str | None = None


def _check(category: str, radius_km: float, plan: PlanTier | None) -> None:
    if category not in get_categories():
        raise ApiError(422, ErrorClass.VALIDATION, "Unknown category", "category")
    problem = radius_error(plan, radius_km)
    if problem:
        raise ApiError(422, ErrorClass.VALIDATION, problem, "radius_km")


@router.get("/nearby", response_model=NearbyView)
def nearby(
    category: str,
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radius_km: float = Query(default=3.0, ge=MIN_RADIUS_KM, le=MAX_RADIUS_KM),
    plan: PlanTier | None = None,
    session: Session = Depends(get_session),
) -> NearbyView:
    _check(category, radius_km, plan)
    rows = session.execute(
        select(Business).where(
            Business.category == category,
            Business.latitude.is_not(None),
            Business.longitude.is_not(None),
            Business.participation_status.not_in([str(s) for s in HIDDEN]),
            Business.opted_out_at.is_(None),
        )
    ).scalars()
    items: list[NearbyBusiness] = []
    from_osm = False
    for b in rows:
        d = distance_km(lat, lng, b.latitude, b.longitude)
        if d > radius_km:
            continue
        status = ParticipationStatus(b.participation_status)
        from_osm = from_osm or b.external_source == "osm"
        items.append(
            NearbyBusiness(
                id=str(b.id),
                name=b.name,
                kind=BusinessKind(b.kind),
                participation_status=status,
                contactable=status in CALLABLE,
                distance_km=round(d, 2),
                bearing_deg=round(bearing_deg(lat, lng, b.latitude, b.longitude), 1),
                address=b.address,
                source=b.source,
            )
        )
    items.sort(key=lambda i: (i.distance_km, i.id))
    return NearbyView(
        businesses=items[:MAX_LISTED], attribution=osm.ATTRIBUTION if from_osm else None
    )


class DiscoverRequest(BaseModel):
    category: str
    lat: float
    lng: float
    radius_km: float = 3.0
    plan: PlanTier | None = None


class DiscoverResult(BaseModel):
    found: int
    new: int
    updated: int
    unchanged: int
    without_phone: int
    attribution: str = osm.ATTRIBUTION


@router.post("/discover", response_model=DiscoverResult, dependencies=[Depends(require_access_key)])
def discover(
    body: DiscoverRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> DiscoverResult:
    if not settings.feature_discovery:
        raise ApiError(404, ErrorClass.NOT_FOUND, "Not found")
    if not request.app.state.discover_limiter.allow(_client_key(request)):
        raise ApiError(429, ErrorClass.RATE_LIMITED, "Too many lookups, try again in a minute")
    if not (-90 <= body.lat <= 90 and -180 <= body.lng <= 180):
        raise ApiError(422, ErrorClass.VALIDATION, "Invalid location", "location")
    if not MIN_RADIUS_KM <= body.radius_km <= MAX_RADIUS_KM:
        raise ApiError(422, ErrorClass.VALIDATION, "Radius out of range", "radius_km")
    _check(body.category, body.radius_km, body.plan)
    tags = get_categories()[body.category].osm_tags
    try:
        query = osm.build_query(tags, body.lat, body.lng, body.radius_km)
        payload = osm.fetch(settings.overpass_url, query, settings.discovery_timeout_seconds)
    except Exception as exc:  # network, HTTP or parse: report, never retry in a loop
        log.warning("OpenStreetMap lookup failed: %s", type(exc).__name__)
        raise ApiError(
            503, ErrorClass.PROVIDER_UNAVAILABLE, "OpenStreetMap is not reachable right now"
        ) from exc
    summary = store_discovered(session, osm.parse(payload), body.category, clock())
    session.commit()
    return DiscoverResult(**summary.__dict__)
