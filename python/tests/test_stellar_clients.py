"""Stellar/Soroban client tests (no network)."""

from __future__ import annotations

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


def test_client_errors_propagate():
    def boom_get(_url, _params):
        raise StellarClientError("horizon down")

    with pytest.raises(StellarClientError):
        HorizonClient("https://h", http_get=boom_get).latest_ledger()

    def boom_rpc(_method, _params):
        raise StellarClientError("rpc down")

    with pytest.raises(StellarClientError):
        SorobanRpcClient("https://r", rpc_call=boom_rpc).get_health()
