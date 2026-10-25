"""Load the curated business directory from YAML (Bible 24.1, T3.3). Idempotent: upsert by phone."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Business
from app.domain.enums import BusinessKind, ParticipationStatus

E164 = r"^\+[1-9][0-9]{7,14}$"


class SeedError(ValueError):
    pass


class SeedBusiness(BaseModel):
    name: str = Field(min_length=1)
    phone_e164: str = Field(pattern=E164)
    category: str
    kind: BusinessKind
    participation_status: ParticipationStatus
    consent_recorded_at: datetime | None = None
    consent_note: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    address: str | None = None
    best_call_window: str | None = None
    source: Literal["curated_seed"] = "curated_seed"

    @field_validator("consent_recorded_at")
    @classmethod
    def _tz_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("consent_recorded_at must include a timezone offset")
        return v

    @model_validator(mode="after")
    def _consent_required(self) -> SeedBusiness:
        callable_status = self.participation_status in {
            ParticipationStatus.CONSENTED,
            ParticipationStatus.TEST_LINE,
        }
        if callable_status and (self.consent_recorded_at is None or not self.consent_note):
            raise ValueError(
                f"{self.name}: {self.participation_status} requires consent_recorded_at "
                "and consent_note (no consent record, no calls)"
            )
        if self.kind is BusinessKind.TEAM_TEST_LINE and (
            self.participation_status is not ParticipationStatus.TEST_LINE
        ):
            raise ValueError(f"{self.name}: a team test line must have status TEST_LINE")
        return self


def read_seed(path: Path) -> list[SeedBusiness]:
    if not path.is_file():
        raise SeedError(f"seed file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = data.get("businesses")
    if not isinstance(rows, list):
        raise SeedError("seed file must contain a 'businesses' list")
    parsed: list[SeedBusiness] = []
    for i, row in enumerate(rows, start=1):
        try:
            parsed.append(SeedBusiness.model_validate(row))
        except ValueError as exc:
            raise SeedError(f"entry {i}: {exc}") from exc
    phones = [b.phone_e164 for b in parsed]
    if len(phones) != len(set(phones)):
        raise SeedError("duplicate phone numbers in seed file")
    return parsed


def load_seed(session: Session, path: Path) -> dict[str, int]:
    """Upsert businesses by phone number. Never downgrades an opt-out."""
    created = updated = kept_opt_out = 0
    for entry in read_seed(path):
        existing = session.execute(
            select(Business).where(Business.phone_e164 == entry.phone_e164)
        ).scalar_one_or_none()
        values = entry.model_dump(mode="python")
        if existing is None:
            session.add(Business(**values))
            created += 1
            continue
        if existing.opted_out_at is not None:
            # An opt-out is permanent: re-seeding must not make the business callable again.
            kept_opt_out += 1
            continue
        for key, value in values.items():
            setattr(existing, key, value)
        updated += 1
    session.commit()
    return {"created": created, "updated": updated, "opt_outs_preserved": kept_opt_out}
