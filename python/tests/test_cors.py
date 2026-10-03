"""CORS configuration tests."""

from __future__ import annotations


def test_preflight_allowed_for_configured_origin(cors_client):
    response = cors_client.options(
        "/api/v1/analyze",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.example.com"


def test_origin_not_echoed_when_unconfigured(client):
    response = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers
