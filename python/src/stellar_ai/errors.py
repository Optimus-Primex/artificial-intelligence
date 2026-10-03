"""Consistent JSON error responses.

Every error is shaped as ``{"error": {message, status, request_id, ...}}`` so
clients can handle failures uniformly (see ``docs/errors.md``).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error(
    status: int,
    message,
    request: Request,
    details=None,
) -> JSONResponse:
    payload: dict = {
        "message": message,
        "status": status,
        "request_id": _request_id(request),
    }
    if details is not None:
        payload["details"] = details
    return JSONResponse(status_code=status, content={"error": payload})


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        response = _error(exc.status_code, exc.detail, request)
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return _error(422, "validation error", request, details=exc.errors())
