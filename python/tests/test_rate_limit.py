"""Rate limiting tests."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.requests import Request

from stellar_ai.config import Settings
from stellar_ai.rate_limit import RateLimiter, rate_limit_identity

BEARER = {"Authorization": "Bearer secret-key"}


def _request(headers: dict[str, str] | None = None, host: str = "203.0.113.7") -> Request:
    raw_headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/chat",
            "headers": raw_headers,
            "client": (host, 1234),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )


def test_requests_over_the_limit_return_429(client_factory):
    client = client_factory(
        api_keys="secret-key",
        rate_limit_requests=2,
        rate_limit_window_seconds=60,
    )

    first = client.get("/api/v1/network/status", headers=BEARER)
    second = client.get("/api/v1/network/status", headers=BEARER)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers["X-RateLimit-Remaining"] == "0"

    response = client.get("/api/v1/network/status", headers=BEARER)
    assert response.status_code == 429
    assert response.headers["X-RateLimit-Limit"] == "2"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert int(response.headers["Retry-After"]) >= 1

    body = response.json()
    assert body["error"]["message"] == "rate limit exceeded"
    assert body["error"]["status"] == 429
    assert body["error"]["request_id"]
    assert response.headers["X-Request-ID"] == body["error"]["request_id"]


def test_limits_are_per_api_key(client_factory):
    client = client_factory(
        api_keys="key-a,key-b",
        rate_limit_requests=1,
        rate_limit_window_seconds=60,
    )
    key_a = {"Authorization": "Bearer key-a"}
    key_b = {"Authorization": "Bearer key-b"}

    assert client.get("/api/v1/network/status", headers=key_a).status_code == 200
    assert client.get("/api/v1/network/status", headers=key_a).status_code == 429
    assert client.get("/api/v1/network/status", headers=key_b).status_code == 200


def test_limits_are_per_ip_when_auth_is_disabled(app_factory):
    app = app_factory(rate_limit_requests=1, rate_limit_window_seconds=60)
    first_client = TestClient(app, client=("198.51.100.1", 1000))
    second_client = TestClient(app, client=("198.51.100.2", 1000))

    assert first_client.get("/api/v1/network/status").status_code == 200
    assert first_client.get("/api/v1/network/status").status_code == 429
    assert second_client.get("/api/v1/network/status").status_code == 200


def test_health_and_ready_are_not_limited(client_factory):
    client = client_factory(rate_limit_requests=1, rate_limit_window_seconds=60)

    for _ in range(3):
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200

    assert client.get("/api/v1/network/status").status_code == 200
    assert client.get("/api/v1/network/status").status_code == 429


def test_rate_limiting_can_be_disabled(client_factory):
    client = client_factory(rate_limit_enabled=False, rate_limit_requests=1)

    for _ in range(5):
        assert client.get("/api/v1/network/status").status_code == 200


def test_rate_limit_settings_come_from_env(monkeypatch):
    monkeypatch.setenv("STELLAR_AI_RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("STELLAR_AI_RATE_LIMIT_REQUESTS", "7")
    monkeypatch.setenv("STELLAR_AI_RATE_LIMIT_WINDOW_SECONDS", "2.5")

    settings = Settings(_env_file=None)
    assert settings.rate_limit_enabled is False
    assert settings.rate_limit_requests == 7
    assert settings.rate_limit_window_seconds == 2.5


def test_rate_limit_settings_are_validated():
    with pytest.raises(ValidationError):
        Settings(rate_limit_requests=0)
    with pytest.raises(ValidationError):
        Settings(rate_limit_window_seconds=0)


def test_identity_uses_a_hashed_configured_key():
    settings = Settings(api_keys="secret-key")
    identity = rate_limit_identity(_request(BEARER), settings)

    assert identity.startswith("key:")
    assert "secret-key" not in identity
    assert len(identity) == len("key:") + 64


def test_identity_falls_back_to_ip_for_unknown_keys():
    settings = Settings(api_keys="secret-key")
    unknown = {"Authorization": "Bearer not-a-configured-key"}

    assert rate_limit_identity(_request(unknown), settings) == "ip:203.0.113.7"
    assert rate_limit_identity(_request(), settings) == "ip:203.0.113.7"


def test_window_slides():
    async def scenario():
        limiter = RateLimiter(limit=2, window_seconds=10)
        assert (await limiter.consume("identity", now=0)).allowed
        assert (await limiter.consume("identity", now=1)).allowed

        blocked = await limiter.consume("identity", now=2)
        assert blocked.allowed is False
        assert blocked.remaining == 0
        assert blocked.reset_after == 8

        allowed = await limiter.consume("identity", now=12.1)
        assert allowed.allowed is True
        assert allowed.remaining == 1

    asyncio.run(scenario())
