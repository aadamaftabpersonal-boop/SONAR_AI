from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import misc, searches
from app.api.deps import SlidingWindowLimiter
from app.api.errors import install_error_handlers
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Sonar", version="0.1.0")
    app.state.search_limiter = SlidingWindowLimiter(settings.rate_limit_search_per_minute)

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
    return app


app = create_app()
