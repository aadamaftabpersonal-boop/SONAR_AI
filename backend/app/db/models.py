"""SQLAlchemy models. Shape follows Bible 19.2 (text + CHECK instead of PG enums, D-008)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain import enums


def in_values(column: str, values: type[StrEnum] | list[str]) -> str:
    names = [m.value for m in values] if isinstance(values, type) else values
    quoted = ",".join(f"'{n}'" for n in names)
    return f"{column} IN ({quoted})"


# Part I database values. Wave 2 values (e.g. NOT_CALLED_STOP_RULE) arrive with migration 0002.
RESPONSE_ORIGINS = ["LIVE_CALL", "SIMULATED"]


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Business(Base):
    __tablename__ = "businesses"
    __table_args__ = (
        CheckConstraint(r"phone_e164 ~ '^\+[1-9][0-9]{7,14}$'", name="ck_businesses_phone"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_businesses_lat"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_businesses_lng"),
        CheckConstraint(in_values("kind", enums.BusinessKind), name="ck_businesses_kind"),
        CheckConstraint(
            in_values("participation_status", enums.ParticipationStatus),
            name="ck_businesses_participation",
        ),
        CheckConstraint(
            "participation_status NOT IN ('CONSENTED','TEST_LINE') "
            "OR consent_recorded_at IS NOT NULL",
            name="ck_businesses_consent_recorded",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone_e164: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    participation_status: Mapped[str] = mapped_column(Text, nullable=False)
    consent_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_note: Mapped[str | None] = mapped_column(Text)
    opted_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    best_call_window: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _now()


class SearchJob(Base):
    __tablename__ = "search_jobs"
    __table_args__ = (
        CheckConstraint("char_length(query_text) <= 500", name="ck_search_jobs_query_len"),
        CheckConstraint("radius_km > 0 AND radius_km <= 25", name="ck_search_jobs_radius"),
        CheckConstraint(in_values("status", enums.SearchStatus), name="ck_search_jobs_status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_query: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    category: Mapped[str | None] = mapped_column(Text)
    center_lat: Mapped[float | None] = mapped_column(Float)
    center_lng: Mapped[float | None] = mapped_column(Float)
    radius_km: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    status: Mapped[str] = mapped_column(Text, nullable=False)
    demo_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    force_fresh: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    planned_targets: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    clarification: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _now()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CallAttempt(Base):
    __tablename__ = "call_attempts"
    __table_args__ = (
        CheckConstraint("attempt_number BETWEEN 1 AND 5", name="ck_call_attempts_number"),
        CheckConstraint(
            in_values("provider", ["bolna", "simulated"]), name="ck_call_attempts_provider"
        ),
        CheckConstraint(in_values("status", enums.CallStatus), name="ck_call_attempts_status"),
        UniqueConstraint("search_job_id", "business_id", "attempt_number", name="uq_attempt_slot"),
        UniqueConstraint("provider", "provider_call_id", name="uq_attempt_provider_call"),
        Index("ix_call_attempts_status_not_before", "status", "not_before"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    search_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("search_jobs.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_call_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    provider_status: Mapped[str | None] = mapped_column(Text)
    not_before: Mapped[datetime] = _now()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    cost_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    cost_currency: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    error_class: Mapped[str | None] = mapped_column(Text)
    retry_eligible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _now()


class ProviderEvent(Base):
    __tablename__ = "provider_events"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_call_id",
            "provider_status",
            "payload_sha256",
            name="uq_provider_event",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    call_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("call_attempts.id", ondelete="SET NULL")
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_call_id: Mapped[str | None] = mapped_column(Text)
    provider_status: Mapped[str | None] = mapped_column(Text)
    payload_sha256: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = _now()
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BusinessResponse(Base):
    __tablename__ = "business_responses"
    __table_args__ = (
        CheckConstraint(in_values("data_origin", RESPONSE_ORIGINS), name="ck_responses_origin"),
        CheckConstraint(
            in_values("availability", enums.Availability), name="ck_responses_availability"
        ),
        CheckConstraint(
            in_values("exact_match", enums.ExactMatch), name="ck_responses_exact_match"
        ),
        CheckConstraint(
            in_values("extraction_status", enums.ExtractionStatus), name="ck_responses_extraction"
        ),
        CheckConstraint(
            in_values("verification_status", enums.VerificationStatus),
            name="ck_responses_verification",
        ),
        CheckConstraint(
            "open_status IS NULL OR open_status IN ('OPEN','CLOSED','UNKNOWN')",
            name="ck_responses_open_status",
        ),
        Index("ix_responses_business_time", "business_id", "answer_timestamp"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    # UNIQUE is the idempotency anchor: a result can only be written once per attempt.
    call_attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call_attempts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    search_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("search_jobs.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    data_origin: Mapped[str] = mapped_column(Text, nullable=False)
    availability: Mapped[str] = mapped_column(Text, nullable=False)
    exact_match: Mapped[str] = mapped_column(Text, nullable=False)
    matched_attributes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    alternative_note: Mapped[str | None] = mapped_column(Text)
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    price_currency: Mapped[str | None] = mapped_column(Text)
    price_note: Mapped[str | None] = mapped_column(Text)
    quantity_reported: Mapped[int | None] = mapped_column(Integer)
    wait_time_minutes: Mapped[int | None] = mapped_column(Integer)
    open_status: Mapped[str | None] = mapped_column(Text)
    answer_summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_excerpt: Mapped[str | None] = mapped_column(Text)
    evidence_validated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    provider_extracted: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    provider_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    extraction_status: Mapped[str] = mapped_column(Text, nullable=False)
    validation_flags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    verification_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'REPORTED_BY_PHONE'")
    )
    answer_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    availability_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = _now()
    actor: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    search_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    business_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
