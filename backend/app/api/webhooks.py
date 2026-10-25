"""POST /api/webhooks/bolna/{secret_token} (Bible 20.6).

Authenticate, persist the raw event, return 200 fast, finalize in the background. The body is
never used to write a result: finalization pulls the provider's own record (D-005).
"""

from __future__ import annotations

import hmac
import json
from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_clock, get_providers, get_session_factory
from app.api.errors import ApiError
from app.config import Settings, get_settings
from app.domain.enums import ErrorClass
from app.providers.registry import ProviderRegistry
from app.services.events import FINALIZE, record_event
from app.services.finalizer import finalize_attempt

router = APIRouter(prefix="/api/webhooks")


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.post("/bolna/{secret_token}")
async def bolna_webhook(
    secret_token: str,
    request: Request,
    background: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    session_factory: sessionmaker[Session] = Depends(get_session_factory),
    providers: ProviderRegistry = Depends(get_providers),
    clock: Callable[[], datetime] = Depends(get_clock),
) -> dict[str, bool]:
    expected = settings.webhook_secret_token
    # fail closed: an unset token must never mean "open"
    if not expected or not hmac.compare_digest(secret_token, expected):
        raise ApiError(401, ErrorClass.WEBHOOK_UNAUTHENTICATED, "Invalid webhook token")

    allowed = {ip.strip() for ip in settings.webhook_allowed_ips.split(",") if ip.strip()}
    if allowed and _client_ip(request) not in allowed:
        raise ApiError(401, ErrorClass.WEBHOOK_UNAUTHENTICATED, "Source not allowed")

    raw = await request.body()
    if len(raw) > settings.webhook_max_body_bytes:
        raise ApiError(413, ErrorClass.WEBHOOK_MALFORMED, "Webhook body too large")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ApiError(400, ErrorClass.WEBHOOK_MALFORMED, "Webhook body is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ApiError(400, ErrorClass.WEBHOOK_MALFORMED, "Webhook body must be a JSON object")

    with session_factory() as session:
        outcome = record_event(session, "bolna", payload)
        session.commit()

    if outcome.action == FINALIZE and outcome.attempt_id is not None:
        background.add_task(
            finalize_attempt, session_factory, outcome.attempt_id, providers, settings, clock
        )
    return {"ok": True}
