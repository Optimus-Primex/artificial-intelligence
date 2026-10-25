"""In-memory rate limiting for the HTTP API.

The limiter uses a sliding window per identity. An identity is a valid API key
when authentication is configured, otherwise the client IP. It is intentionally
in-process: the service is deployed as a single worker today, so no shared store
is needed. See the README for the configuration variables.

Only ``/api/`` paths are limited; ``/health`` and ``/ready`` remain available so
load balancers and orchestrators can always probe the service.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

from .config import Settings

LIMITED_PATH_PREFIX = "/api/"
_RATE_LIMIT_ERROR = "rate limit exceeded"


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of one rate-limit check."""

    allowed: bool
    limit: int
    remaining: int
    reset_after: float


class RateLimiter:
    """Sliding-window counter keyed by an opaque identity."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        if limit < 1:
            raise ValueError("rate limit must be at least 1")
        if window_seconds <= 0:
            raise ValueError("rate limit window must be positive")
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()
        self._checks = 0

    async def consume(self, identity: str, now: float | None = None) -> RateLimitResult:
        """Record a hit and report whether the identity is still under the limit."""

        current = time.monotonic() if now is None else now
        async with self._lock:
            hits = self._hits.setdefault(identity, deque())
            cutoff = current - self._window
            while hits and hits[0] <= cutoff:
                hits.popleft()

            self._checks += 1
            if self._checks % 1024 == 0:
                self._prune()

            if len(hits) >= self._limit:
                reset_after = max(0.0, hits[0] + self._window - current)
                return RateLimitResult(
                    allowed=False,
                    limit=self._limit,
                    remaining=0,
                    reset_after=reset_after,
                )

            hits.append(current)
            oldest = hits[0]
            return RateLimitResult(
                allowed=True,
                limit=self._limit,
                remaining=self._limit - len(hits),
                reset_after=max(0.0, oldest + self._window - current),
            )

    def _prune(self) -> None:
        """Drop identities whose window is empty."""

        for identity in [key for key, hits in self._hits.items() if not hits]:
            del self._hits[identity]


def bearer_token(request: Request) -> str | None:
    """Return the bearer token from the Authorization header, if any."""

    header = request.headers.get("Authorization")
    if not header or not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    return token or None


def rate_limit_identity(request: Request, settings: Settings) -> str:
    """Choose the bucket for a request: a configured API key, else the client IP.

    Unrecognised tokens are deliberately bucketed by IP so a caller cannot
    sidestep the limit by sending random Authorization headers.
    """

    token = bearer_token(request)
    if token and token in settings.api_key_set:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return f"key:{digest}"

    client = request.client
    host = client.host if client is not None else "unknown"
    return f"ip:{host}"


def _headers(result: RateLimitResult) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(math.ceil(result.reset_after)),
    }


def _too_many_requests(request: Request, result: RateLimitResult) -> JSONResponse:
    headers = _headers(result)
    headers["Retry-After"] = str(max(1, math.ceil(result.reset_after)))
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "message": _RATE_LIMIT_ERROR,
                "status": 429,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
        headers=headers,
    )


def install_rate_limit_middleware(app: FastAPI, settings: Settings) -> None:
    """Attach the limiter to the app when it is enabled."""

    if not settings.rate_limit_enabled:
        return

    limiter = RateLimiter(
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        if not request.url.path.startswith(LIMITED_PATH_PREFIX):
            return await call_next(request)

        result = await limiter.consume(rate_limit_identity(request, settings))
        if not result.allowed:
            return _too_many_requests(request, result)

        response = await call_next(request)
        for name, value in _headers(result).items():
            response.headers.setdefault(name, value)
        return response
