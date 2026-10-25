"""Uniform error envelope (Bible 20.1)."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.enums import ErrorClass
from app.domain.schemas import ErrorBody, ErrorEnvelope

log = logging.getLogger("sonar.api")


class ApiError(Exception):
    def __init__(
        self, status_code: int, code: ErrorClass, message: str, field: str | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or uuid.uuid4().hex


def envelope(
    request: Request, status: int, code: ErrorClass, message: str, field: str | None = None
) -> JSONResponse:
    body = ErrorEnvelope(
        error=ErrorBody(code=code, message=message, field=field, request_id=_request_id(request))
    )
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return envelope(request, exc.status_code, exc.code, exc.message, exc.field)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        return envelope(
            request, 422, ErrorClass.VALIDATION, first.get("msg", "invalid request"), loc or None
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = ErrorClass.NOT_FOUND if exc.status_code == 404 else ErrorClass.INTERNAL
        return envelope(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # never leak internals (stack traces, SQL, provider payloads) to the client
        log.exception("unhandled error request_id=%s", _request_id(request))
        return envelope(request, 500, ErrorClass.INTERNAL, "Internal error")
