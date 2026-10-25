"""Shared dependencies: access key, rate limit, clock, settings (Bible 20, D-009)."""

from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session, sessionmaker

from app.api.errors import ApiError
from app.config import Settings, get_settings
from app.db.session import get_engine, make_session_factory
from app.domain.enums import ErrorClass
from app.providers.registry import ProviderRegistry


def get_session_factory() -> sessionmaker[Session]:
    """Used by background work that outlives a request. Tests override it."""
    return make_session_factory(get_engine())


def get_providers(request: Request) -> ProviderRegistry:
    return request.app.state.providers


def get_clock() -> Callable[[], datetime]:
    """Overridable in tests so call-window logic is deterministic."""
    return lambda: datetime.now(UTC)


class SlidingWindowLimiter:
    """Small in-memory per-key limiter. Single process only, which matches the MVP (D-006)."""

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def require_access_key(
    x_sonar_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.sonar_access_key
    if not expected:
        # fail closed: an unconfigured key must never mean "open"
        raise ApiError(401, ErrorClass.UNAUTHORIZED, "Access key is not configured on the server")
    if x_sonar_key is None or not hmac.compare_digest(x_sonar_key, expected):
        raise ApiError(401, ErrorClass.UNAUTHORIZED, "Missing or invalid access key")


def rate_limit_search(request: Request) -> None:
    limiter: SlidingWindowLimiter = request.app.state.search_limiter
    if not limiter.allow(_client_key(request)):
        raise ApiError(429, ErrorClass.RATE_LIMITED, "Too many searches, try again in a minute")
