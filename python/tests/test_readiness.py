"""Readiness vs liveness tests."""

from __future__ import annotations


def test_ready_when_dependencies_are_up(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["network"] == "testnet"


def test_not_ready_when_dependencies_are_down(error_client):
    response = error_client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
