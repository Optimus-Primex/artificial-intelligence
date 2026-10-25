"""API endpoint tests."""

from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "stellar-ai", "provider": "fake"}


def test_network_status(client):
    response = client.get("/api/v1/network/status", params={"network": "testnet"})
    assert response.status_code == 200
    body = response.json()
    assert body["healthy"] is True
    assert body["latest_ledger"] == 100
    assert body["network"] == "testnet"


def test_network_status_uses_default_network(client):
    body = client.get("/api/v1/network/status").json()
    assert body["network"] == "testnet"


def test_unknown_network_is_a_400(client):
    response = client.get("/api/v1/network/status", params={"network": "regtest"})
    assert response.status_code == 400


def test_analyze(client):
    response = client.post("/api/v1/analyze", json={"network": "testnet"})
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "fake"
    assert "testnet" in body["summary"]
    assert body["metrics"]["latest_ledger"] == 100


def test_analyze_flags_whale_payments(payments_client):
    response = payments_client.post("/api/v1/analyze", json={"network": "testnet"})
    assert response.status_code == 200
    body = response.json()
    assert body["payments"]["asset"] == "XLM"
    assert body["payments"]["payments_scanned"] == 3
    assert body["payments"]["whale_count"] == 1
    assert body["alerts"][0]["amount"] == 250000.0
    assert body["alerts"][0]["transaction_hash"] == "whale-tx"
    assert "whale" in body["summary"].lower()


def test_analyze_accepts_asset_and_threshold_overrides(payments_client):
    response = payments_client.post(
        "/api/v1/analyze",
        json={
            "network": "testnet",
            "asset": "USDC:GISSUER",
            "whale_threshold": 500000,
            "payment_limit": 10,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["payments"]["asset"] == "USDC:GISSUER"
    assert body["payments"]["threshold"] == 500000.0
    assert body["payments"]["limit"] == 10
    assert body["payments"]["whale_count"] == 1
    assert body["alerts"][0]["amount"] == 999999.0


def test_analyze_below_threshold_returns_no_alerts(payments_client):
    body = payments_client.post(
        "/api/v1/analyze",
        json={"network": "testnet", "whale_threshold": 10000000},
    ).json()
    assert body["payments"]["whale_count"] == 0
    assert body["alerts"] == []
    assert "No transfers" in body["summary"]


def test_analyze_rejects_non_positive_threshold(client):
    response = client.post("/api/v1/analyze", json={"whale_threshold": 0})
    assert response.status_code == 422


def test_chat_grounds_the_prompt(client, provider):
    response = client.post("/api/v1/chat", json={"message": "Is the network healthy?"})
    assert response.status_code == 200
    assert response.json()["answer"] == "the network looks healthy"
    assert provider.prompts
    assert "Is the network healthy?" in provider.prompts[0]
    assert "testnet" in provider.prompts[0]


def test_chat_rejects_empty_message(client):
    assert client.post("/api/v1/chat", json={"message": ""}).status_code == 422


def test_stellar_error_returns_502(error_client):
    assert error_client.get("/api/v1/network/status").status_code == 502
