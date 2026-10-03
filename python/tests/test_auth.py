"""API key authentication tests."""

from __future__ import annotations


def test_health_is_open(secured_client):
    assert secured_client.get("/health").status_code == 200


def test_ready_is_open(secured_client):
    assert secured_client.get("/ready").status_code == 200


def test_missing_key_is_rejected(secured_client):
    response = secured_client.get("/api/v1/network/status")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_wrong_key_is_rejected(secured_client):
    response = secured_client.get(
        "/api/v1/network/status", headers={"Authorization": "Bearer nope"}
    )
    assert response.status_code == 401


def test_valid_key_is_accepted(secured_client):
    response = secured_client.get(
        "/api/v1/network/status", headers={"Authorization": "Bearer secret-key"}
    )
    assert response.status_code == 200


def test_auth_disabled_without_keys(client):
    # The default `client` fixture configures no keys, so calls are allowed.
    assert client.get("/api/v1/network/status").status_code == 200
