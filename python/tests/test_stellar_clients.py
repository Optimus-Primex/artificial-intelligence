"""Stellar/Soroban client tests (no network)."""

from __future__ import annotations

import httpx
import pytest

from stellar_ai.stellar import HorizonClient, SorobanRpcClient, StellarClientError


def test_horizon_latest_ledger():
    captured = {}

    def http_get(url, params):
        captured["url"] = url
        captured["params"] = params
        return {"_embedded": {"records": [{"sequence": 7}]}}

    client = HorizonClient("https://horizon.example/", http_get=http_get)
    assert client.latest_ledger() == {"sequence": 7}
    assert captured["url"] == "https://horizon.example/ledgers"
    assert captured["params"] == {"order": "desc", "limit": 1}


def test_horizon_no_ledgers_returns_none():
    client = HorizonClient("https://h", http_get=lambda _u, _p: {"_embedded": {"records": []}})
    assert client.latest_ledger() is None


def test_soroban_get_health():
    def rpc_call(method, _params):
        assert method == "getHealth"
        return {"status": "healthy"}

    client = SorobanRpcClient("https://rpc.example", rpc_call=rpc_call)
    assert client.get_health() == {"status": "healthy"}


def test_soroban_get_events_params():
    captured = {}

    def rpc_call(method, params):
        captured["method"] = method
        captured["params"] = params
        return {"events": [], "latestLedger": 10}

    client = SorobanRpcClient("https://rpc.example", rpc_call=rpc_call)
    result = client.get_events(100, ["C1", "C2"], 50)
    assert result == {"events": [], "latestLedger": 10}
    assert captured["method"] == "getEvents"
    assert captured["params"] == {
        "startLedger": 100,
        "filters": [{"type": "contract", "contractIds": ["C1", "C2"]}],
        "limit": 50,
        "xdrFormat": "base64",
    }

    client.get_events(100, "C1", 10, xdr_format=None)
    assert captured["params"] == {
        "startLedger": 100,
        "filters": [{"type": "contract", "contractIds": ["C1"]}],
        "limit": 10,
    }

    client.get_events(100)
    assert captured["params"]["filters"] == [{"type": "contract"}]


def test_soroban_get_events_validates_arguments():
    client = SorobanRpcClient("https://rpc.example", rpc_call=lambda _m, _p: {})
    with pytest.raises(ValueError, match="start_ledger"):
        client.get_events(0)
    with pytest.raises(ValueError, match="start_ledger"):
        client.get_events("100")
    with pytest.raises(ValueError, match="limit"):
        client.get_events(1, limit=0)
    with pytest.raises(ValueError, match="limit"):
        client.get_events(1, limit=201)
    with pytest.raises(ValueError, match="limit"):
        client.get_events(1, limit="10")


def test_soroban_latest_ledger_aliases():
    def rpc_call(method, _params):
        if method == "getNetwork":
            return {"friendbotUrl": "https://friendbot.example"}
        return {"sequence": 42}

    client = SorobanRpcClient("https://rpc.example", rpc_call=rpc_call)
    assert client.latest_ledger() == {"sequence": 42}
    assert client.get_latest_ledger() == {"sequence": 42}
    assert client.get_network() == {"friendbotUrl": "https://friendbot.example"}


def test_client_errors_propagate():
    def boom_get(_url, _params):
        raise StellarClientError("horizon down")

    with pytest.raises(StellarClientError):
        HorizonClient("https://h", http_get=boom_get).latest_ledger()

    def boom_rpc(_method, _params):
        raise StellarClientError("rpc down")

    with pytest.raises(StellarClientError):
        SorobanRpcClient("https://r", rpc_call=boom_rpc).get_health()


# -- default httpx transport paths -----------------------------------------
def _response(status_code=200, *, json=None, text=None) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=json,
        text=text,
        request=httpx.Request("GET", "https://example.test"),
    )


def test_horizon_uses_httpx_by_default(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        assert url == "https://horizon.example/ledgers"
        return _response(200, json={"_embedded": {"records": [{"sequence": 1}]}})

    monkeypatch.setattr(httpx, "get", fake_get)
    assert HorizonClient("https://horizon.example").latest_ledger() == {"sequence": 1}


def test_horizon_http_error_becomes_client_error(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _response(500))
    with pytest.raises(StellarClientError):
        HorizonClient("https://horizon.example").latest_ledger()


def test_horizon_account(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _response(200, json={"id": "G"}))
    assert HorizonClient("https://h").account("G") == {"id": "G"}


def test_horizon_recent_payments():
    captured = {}

    def http_get(url, params):
        captured["url"] = url
        captured["params"] = params
        return {"_embedded": {"records": [{"type": "payment", "amount": "1"}]}}

    client = HorizonClient("https://horizon.example/", http_get=http_get)
    records = client.recent_payments(limit=10)
    assert records == [{"type": "payment", "amount": "1"}]
    assert captured["url"] == "https://horizon.example/payments"
    assert captured["params"] == {"order": "desc", "limit": 10, "include_failed": "false"}


def test_horizon_recent_payments_missing_embedded():
    client = HorizonClient("https://h", http_get=lambda _u, _p: {})
    assert client.recent_payments() == []


def test_horizon_invalid_json_becomes_client_error(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _response(200, text="<html>oops</html>"))
    with pytest.raises(StellarClientError, match="invalid JSON"):
        HorizonClient("https://horizon.example").latest_ledger()


def test_soroban_uses_httpx_by_default(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: _response(
            200, json={"jsonrpc": "2.0", "id": 1, "result": {"status": "healthy"}}
        ),
    )
    assert SorobanRpcClient("https://r").get_health() == {"status": "healthy"}


def test_soroban_rpc_error_becomes_client_error(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: _response(
            200, json={"jsonrpc": "2.0", "id": 1, "error": {"message": "boom"}}
        ),
    )
    with pytest.raises(StellarClientError):
        SorobanRpcClient("https://r").get_health()


def test_soroban_invalid_json_becomes_client_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _response(200, text="not json"))
    with pytest.raises(StellarClientError):
        SorobanRpcClient("https://r").latest_ledger()


def test_soroban_http_error_becomes_client_error(monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _response(503))
    with pytest.raises(StellarClientError):
        SorobanRpcClient("https://r").get_health()
