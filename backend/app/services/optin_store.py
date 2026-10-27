"""Database side of shop self opt-in (D-061). Every change leaves an audit event."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Business, OptInToken
from app.db.repositories import AttemptRepo, AuditRepo
from app.domain.enums import BusinessKind, ParticipationStatus
from app.services.optin import (
    JoinForm,
    JoinRequest,
    consent_note,
    hash_token,
    new_token,
    window_for_selector,
)


class InviteRefused(ValueError):
    pass


@dataclass
class Redeemed:
    business: Business
    stop_token: str  # shown once on the thank-you page; only its hash is stored


def issue_invite(
    session: Session, business_id: uuid.UUID, created_by: str, now: datetime, days: int
) -> str:
    business = session.get(Business, business_id)
    if business is None:
        raise InviteRefused("no such business")
    if business.opted_out_at is not None or business.participation_status in {
        ParticipationStatus.OPTED_OUT,
        ParticipationStatus.DECLINED,
    }:
        raise InviteRefused("this shop said no or asked not to be called; it is never re-invited")
    if business.kind != BusinessKind.REAL_BUSINESS:
        raise InviteRefused("team test lines do not need an invite")
    token, digest = new_token()
    session.add(
        OptInToken(
            business_id=business.id,
            token_hash=digest,
            created_by=created_by,
            expires_at=now + timedelta(days=days),
        )
    )
    AuditRepo(session).add(
        created_by, "opt_in_invite_issued", business_id=business.id, detail={"days": days}
    )
    session.flush()
    return token


def invite_for(session: Session, token: str, now: datetime) -> tuple[OptInToken, Business] | None:
    """A usable invite: unused, unexpired, for a shop that has not refused. Else None."""
    row = session.execute(
        select(OptInToken, Business)
        .join(Business, Business.id == OptInToken.business_id)
        .where(OptInToken.token_hash == hash_token(token))
    ).first()
    if row is None:
        return None
    invite, business = row
    if invite.used_at is not None or invite.expires_at <= now:
        return None
    if business.opted_out_at is not None or business.participation_status in {
        ParticipationStatus.OPTED_OUT,
        ParticipationStatus.DECLINED,
    }:
        return None
    return invite, business


def redeem(session: Session, token: str, form: JoinForm, now: datetime) -> Redeemed | None:
    found = invite_for(session, token, now)
    if found is None or not form.agreed():
        return None
    invite, business = found
    stop_token, stop_hash = new_token()
    invite.used_at = now
    business.participation_status = ParticipationStatus.CONSENTED
    business.consent_recorded_at = now
    business.consent_note = consent_note(now, form)
    business.consent_source = "SELF_OPT_IN"
    business.best_call_window = window_for_selector(form.call_window) or business.best_call_window
    business.preferred_language = form.language
    business.stop_token_hash = stop_hash
    business.opt_in_requested_at = None
    business.updated_at = now
    AuditRepo(session).add(
        "shop",
        "self_opt_in",
        business_id=business.id,
        detail={"language": form.language, "window": form.call_window},
    )
    session.flush()
    return Redeemed(business, stop_token)


def stop_calls(session: Session, stop_token: str, now: datetime) -> bool:
    business = session.execute(
        select(Business).where(Business.stop_token_hash == hash_token(stop_token))
    ).scalar_one_or_none()
    if business is None:
        return False
    if business.opted_out_at is None:
        business.opted_out_at = now
    business.participation_status = ParticipationStatus.OPTED_OUT
    business.updated_at = now
    cancelled = AttemptRepo(session).cancel_pending_for_business(business.id, "OPTED_OUT")
    AuditRepo(session).add(
        "shop", "opt_out_via_stop_link", business_id=business.id, detail={"cancelled": cancelled}
    )
    session.flush()
    return True


def request_to_join(session: Session, form: JoinRequest, now: datetime) -> None:
    """Record a request from the public form. Never callable; a teammate must check the number
    belongs to the shop and then issue an invite. The caller always gets the same reply, so the
    form cannot be used to learn which numbers Sonar knows."""
    phone = form.phone_e164()
    if phone is None or form.is_bot():
        return
    business = session.execute(
        select(Business).where(Business.phone_e164 == phone)
    ).scalar_one_or_none()
    if business is None:
        session.add(
            Business(
                name=form.shop_name,
                phone_e164=phone,
                address=form.area,
                category=form.category,
                kind=BusinessKind.REAL_BUSINESS,
                source="join_form",
                participation_status=ParticipationStatus.INVITED,
                opt_in_requested_at=now,
            )
        )
        AuditRepo(session).add("public", "join_requested", detail={"category": form.category})
    elif business.participation_status == ParticipationStatus.INVITED:
        business.opt_in_requested_at = business.opt_in_requested_at or now
        AuditRepo(session).add("public", "join_requested_again", business_id=business.id)
    # CONSENTED, TEST_LINE, DECLINED, OPTED_OUT: nothing changes (an opt-out is permanent)
    session.flush()


def pending_requests(session: Session) -> list[Business]:
    return list(
        session.execute(
            select(Business)
            .where(
                Business.participation_status == ParticipationStatus.INVITED,
                Business.opt_in_requested_at.is_not(None),
            )
            .order_by(Business.opt_in_requested_at)
        ).scalars()
    )
