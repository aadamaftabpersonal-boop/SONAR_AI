from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import misc, searches, webhooks
from app.api.deps import SlidingWindowLimiter
from app.api.errors import install_error_handlers
from app.config import Settings, bolna_agent_ids, get_settings
from app.db.session import get_engine, make_session_factory
from app.providers.bolna import BolnaVoiceProvider
from app.providers.registry import ProviderRegistry
from app.providers.simulated import SimulatedVoiceProvider
from app.services.orchestrator import Orchestrator

log = logging.getLogger("sonar")

# Demo mode shows a mix of outcomes so judges see honest handling of every case.
DEMO_CYCLE = (
    "available",
    "unavailable",
    "available",
    "no_answer",
    "ambiguous",
    "available",
    "alternative_only",
    "available_no_price",
)


def default_providers(settings: Settings | None = None) -> ProviderRegistry:
    """The simulator is always available. The real provider is registered only when a key and at
    least one agent id are configured, so a missing key can never cause a real call."""
    settings = settings or get_settings()
    registry = ProviderRegistry({"simulated": SimulatedVoiceProvider(cycle=DEMO_CYCLE)})
    agents = bolna_agent_ids(settings)
    if settings.bolna_api_key and agents:
        registry.register(
            "bolna",
            BolnaVoiceProvider(
                settings.bolna_api_key, settings.bolna_api_base_url, agent_ids=agents
            ),
        )
        log.info("live calling enabled for: %s", ", ".join(sorted(agents)))
    else:
        log.info("live calling is not configured; demo mode only")
    return registry


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = None
        if settings.orchestrator_enabled:
            orchestrator = Orchestrator(
                make_session_factory(get_engine()),
                app.state.providers,
                settings,
                lambda: datetime.now(UTC),
            )
            app.state.orchestrator = orchestrator
            task = asyncio.create_task(orchestrator.run_forever())
            log.info("orchestrator started")
        try:
            yield
        finally:
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="Sonar", version="0.1.0", lifespan=lifespan)
    app.state.search_limiter = SlidingWindowLimiter(settings.rate_limit_search_per_minute)
    app.state.providers = default_providers(settings)

    origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Sonar-Key"],
    )

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

    install_error_handlers(app)
    app.include_router(misc.router)
    app.include_router(searches.router)
    app.include_router(webhooks.router)
    return app


app = create_app()
