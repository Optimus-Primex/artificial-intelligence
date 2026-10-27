"""Shared test fixtures and fakes.

No test touches the network: the Stellar clients and LLM provider are injected
with deterministic fakes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from fixtures.soroban_events import EVENTS, EVENTS_RESULT, MALFORMED_EVENT

from stellar_ai.app import create_app
from stellar_ai.config import Settings
from stellar_ai.stellar import HorizonClient, SorobanRpcClient, StellarClientError


def iso(offset_seconds: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(seconds=offset_seconds)).isoformat()


class FakeProvider:
    name = "fake"

    def __init__(self, answer: str = "the network looks healthy"):
        self.answer = answer
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer


def fake_horizon_factory(
    ledger: dict | None = None,
    *,
    error: bool = False,
    ledgers: list[dict] | None = None,
):
    def factory(url: str) -> HorizonClient:
        records = (
            list(ledgers)
            if ledgers is not None
            else [ledger or {"sequence": 100, "closed_at": iso()}]
        )

        def http_get(_url: str, params: dict | None):
            if error:
                raise StellarClientError("horizon unreachable")
            limit = (params or {}).get("limit")
            selected = records[:limit] if isinstance(limit, int) else records
            return {"_embedded": {"records": selected}}

        return HorizonClient(url, http_get=http_get)

    return factory


def fake_rpc_factory(
    health: dict | None = None,
    *,
    error: bool = False,
    events: list[dict] | None = None,
    events_error: bool = False,
    latest_ledger: int = 100,
):
    def factory(url: str) -> SorobanRpcClient:
        def rpc_call(method: str, _params: dict | None):
            if error:
                raise StellarClientError("rpc unreachable")
            if method == "getHealth":
                return health or {"status": "healthy", "protocolVersion": 20}
            if method == "getEvents":
                if events_error:
                    raise StellarClientError("events unavailable")
                result = dict(EVENTS_RESULT if events is None else {"events": events})
                result.setdefault("latestLedger", latest_ledger)
                return result
            return {"sequence": latest_ledger}

        return SorobanRpcClient(url, rpc_call=rpc_call)

    return factory


@pytest.fixture()
def settings() -> Settings:
    return Settings(default_network="testnet")


@pytest.fixture()
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture()
def client(settings, provider) -> TestClient:
    app = create_app(
        settings,
        horizon_factory=fake_horizon_factory(),
        rpc_factory=fake_rpc_factory(),
        provider=provider,
    )
    return TestClient(app)


@pytest.fixture()
def anomalous_client(settings, provider) -> TestClient:
    ledgers = [
        {"sequence": 100, "closed_at": iso(-600)},
        {"sequence": 99, "closed_at": iso(-605)},
        {"sequence": 98, "closed_at": iso(-610)},
    ]
    app = create_app(
        settings,
        horizon_factory=fake_horizon_factory(ledgers=ledgers),
        rpc_factory=fake_rpc_factory(),
        provider=provider,
    )
    return TestClient(app)


@pytest.fixture()
def error_client(settings, provider) -> TestClient:
    app = create_app(
        settings,
        horizon_factory=fake_horizon_factory(error=True),
        rpc_factory=fake_rpc_factory(error=True),
        provider=provider,
    )
    return TestClient(app)


@pytest.fixture()
def events_client(settings, provider) -> TestClient:
    app = create_app(
        settings,
        horizon_factory=fake_horizon_factory(),
        rpc_factory=fake_rpc_factory(events=EVENTS, latest_ledger=105),
        provider=provider,
    )
    return TestClient(app)


@pytest.fixture()
def malformed_events_client(settings, provider) -> TestClient:
    app = create_app(
        settings,
        horizon_factory=fake_horizon_factory(),
        rpc_factory=fake_rpc_factory(events=[MALFORMED_EVENT]),
        provider=provider,
    )
    return TestClient(app)


@pytest.fixture()
def events_error_client(settings, provider) -> TestClient:
    app = create_app(
        settings,
        horizon_factory=fake_horizon_factory(),
        rpc_factory=fake_rpc_factory(events_error=True),
        provider=provider,
    )
    return TestClient(app)


@pytest.fixture()
def secured_client(provider) -> TestClient:
    settings = Settings(default_network="testnet", api_keys="secret-key")
    app = create_app(
        settings,
        horizon_factory=fake_horizon_factory(),
        rpc_factory=fake_rpc_factory(),
        provider=provider,
    )
    return TestClient(app)


@pytest.fixture()
def cors_client(provider) -> TestClient:
    settings = Settings(default_network="testnet", cors_origins="https://app.example.com")
    app = create_app(
        settings,
        horizon_factory=fake_horizon_factory(),
        rpc_factory=fake_rpc_factory(),
        provider=provider,
    )
    return TestClient(app)
