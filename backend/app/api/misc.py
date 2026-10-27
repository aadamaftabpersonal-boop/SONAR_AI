"""Health, public config and the business list (Bible 20.7). No phone number ever leaves here."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_clock
from app.api.errors import ApiError
from app.config import Settings, get_settings
from app.db.session import get_session
from app.domain.enums import BusinessKind, ErrorClass
from app.domain.schemas import MAX_RADIUS_KM, MIN_RADIUS_KM
from app.services import selector
from app.services.categories import get_categories
from app.services.directory import load_candidates
from app.services.result_copy import SIMULATED_BANNER

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness (FR-27)."""
    return {"status": "ok"}


@router.get("/health/ready")
def ready(session: Session = Depends(get_session)) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except Exception as exc:  # any DB failure means not ready
        raise ApiError(503, ErrorClass.INTERNAL, "Database is not reachable") from exc
    return {"status": "ready"}


class CategoryPublic(BaseModel):
    display_name: str
    essential_attributes: list[str]
    required_fields_default: list[str]


class PublicConfig(BaseModel):
    categories: dict[str, CategoryPublic]
    min_radius_km: float
    max_radius_km: float
    max_targets_per_search: int
    simulated_banner: str
    disclaimer: str
    features: dict[str, bool] = {}


@router.get("/api/config/public", response_model=PublicConfig)
def public_config(settings: Settings = Depends(get_settings)) -> PublicConfig:
    return PublicConfig(
        categories={
            name: CategoryPublic(
                display_name=cfg.display_name,
                essential_attributes=cfg.essential_attributes,
                required_fields_default=cfg.required_fields_default,
            )
            for name, cfg in get_categories().items()
        },
        min_radius_km=MIN_RADIUS_KM,
        max_radius_km=MAX_RADIUS_KM,
        max_targets_per_search=settings.max_targets_per_search,
        simulated_banner=SIMULATED_BANNER,
        disclaimer="Sonar reports what the business said. It does not give medical advice.",
        features={"live_ticker": settings.feature_live_ticker},
    )


class BusinessListItem(BaseModel):
    id: str
    name: str
    kind: BusinessKind
    distance_km: float


@router.get("/api/businesses", response_model=list[BusinessListItem])
def list_businesses(
    category: str,
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radius_km: float = Query(default=3.0, ge=MIN_RADIUS_KM, le=MAX_RADIUS_KM),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> list[BusinessListItem]:
    selection = selector.select(
        load_candidates(session, category, clock()),
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        now=clock(),
        max_targets=settings.max_targets_per_search,
        daily_cap=settings.business_daily_call_cap,
        cooldown_minutes=settings.business_cooldown_minutes,
    )
    return [
        BusinessListItem(id=str(t.business_id), name=t.name, kind=t.kind, distance_km=t.distance_km)
        for t in selection.targets
    ]
