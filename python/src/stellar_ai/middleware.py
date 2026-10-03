"""HTTP middleware: request IDs and access logging."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI
from starlette.requests import Request

logger = logging.getLogger("stellar_ai.access")


def install_request_middleware(app: FastAPI) -> None:
    """Attach a request id to every request and log an access line."""

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
