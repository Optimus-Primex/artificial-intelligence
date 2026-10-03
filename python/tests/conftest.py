"""Shared test fixtures and fakes.

No test touches the network: the Stellar clients and LLM provider are injected
with deterministic fakes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

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


def fake_horizon_factory(ledger: dict | None = None, *, error: bool = False):
    def factory(url: str) -> HorizonClient:
        def http_get(_url: str, _params: dict | None):
            if error:
                raise StellarClientError("horizon unreachable")
            return {"_embedded": {"records": [ledger or {"sequence": 100, "closed_at": iso()}]}}

        return HorizonClient(url, http_get=http_get)

    return factory


def fake_rpc_factory(health: dict | None = None, *, error: bool = False):
    def factory(url: str) -> SorobanRpcClient:
        def rpc_call(method: str, _params: dict | None):
            if error:
                raise StellarClientError("rpc unreachable")
            if method == "getHealth":
                return health or {"status": "healthy", "protocolVersion": 20}
            return {"sequence": 100}

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
def error_client(settings, provider) -> TestClient:
    app = create_app(
        settings,
        horizon_factory=fake_horizon_factory(error=True),
        rpc_factory=fake_rpc_factory(error=True),
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
