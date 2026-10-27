"""Store shops found on OpenStreetMap (D-059) without ever making them callable.

New shops become REAL_BUSINESS / INVITED. A shop that already has a consent decision (CONSENTED,
TEST_LINE, DECLINED, OPTED_OUT) keeps it: discovery never overwrites, downgrades or revives one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Business
from app.domain.enums import BusinessKind, ParticipationStatus
from app.services.osm import FoundShop

SOURCE = "osm"
_DECIDED = {
    ParticipationStatus.CONSENTED,
    ParticipationStatus.TEST_LINE,
    ParticipationStatus.DECLINED,
    ParticipationStatus.OPTED_OUT,
}


@dataclass
class DiscoverySummary:
    found: int = 0
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    without_phone: int = 0


def store_discovered(
    session: Session, shops: list[FoundShop], category: str, now: datetime
) -> DiscoverySummary:
    summary = DiscoverySummary(found=len(shops))
    for shop in shops:
        if shop.phone_e164 is None:
            # Without a number a shop cannot be invited or called; it is counted, not stored.
            summary.without_phone += 1
            continue
        existing = (
            session.execute(
                select(Business).where(
                    or_(
                        (Business.external_source == SOURCE)
                        & (Business.external_id == shop.osm_id),
                        Business.phone_e164 == shop.phone_e164,
                    )
                )
            )
            .scalars()
            .first()
        )
        if existing is None:
            session.add(
                Business(
                    name=shop.name,
                    phone_e164=shop.phone_e164,
                    address=shop.address,
                    latitude=shop.lat,
                    longitude=shop.lng,
                    category=category,
                    kind=BusinessKind.REAL_BUSINESS,
                    source=SOURCE,
                    participation_status=ParticipationStatus.INVITED,
                    external_source=SOURCE,
                    external_id=shop.osm_id,
                    discovered_at=now,
                    opening_hours_text=shop.opening_hours,
                )
            )
            summary.new += 1
            continue
        if ParticipationStatus(existing.participation_status) in _DECIDED:
            summary.unchanged += 1  # a consent decision is never touched by discovery
            continue
        existing.name = shop.name
        existing.address = shop.address or existing.address
        existing.latitude, existing.longitude = shop.lat, shop.lng
        existing.opening_hours_text = shop.opening_hours or existing.opening_hours_text
        if existing.external_id is None:
            existing.external_source, existing.external_id = SOURCE, shop.osm_id
        existing.updated_at = now
        summary.updated += 1
    session.flush()
    return summary
