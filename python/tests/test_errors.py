"""Error response shape tests."""

from __future__ import annotations


def test_unknown_network_error_shape(client):
    response = client.get("/api/v1/network/status", params={"network": "regtest"})
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["status"] == 400
    assert "regtest" in error["message"]
    assert error["request_id"]


def test_validation_error_shape(client):
    response = client.post("/api/v1/chat", json={"message": ""})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["status"] == 422
    assert error["message"] == "validation error"
    assert "details" in error


def test_upstream_error_shape(error_client):
    response = error_client.get("/api/v1/network/status")
    assert response.status_code == 502
    assert response.json()["error"]["status"] == 502
