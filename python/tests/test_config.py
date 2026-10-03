"""Configuration tests."""

from __future__ import annotations

import pytest

from stellar_ai.config import NETWORKS, Settings


def test_defaults():
    settings = Settings()
    assert settings.app_name == "stellar-ai"
    assert settings.llm_provider == "static"


def test_resolve_network_is_case_insensitive(settings):
    assert settings.resolve_network("TestNet") == "testnet"
    assert settings.resolve_network(None) == "testnet"


def test_resolve_network_rejects_unknown(settings):
    with pytest.raises(ValueError):
        settings.resolve_network("regtest")


def test_urls_default_per_network(settings):
    assert settings.horizon_url_for("mainnet") == NETWORKS["mainnet"]["horizon"]
    assert settings.rpc_url_for("mainnet") == NETWORKS["mainnet"]["rpc"]


def test_url_overrides_win(settings):
    settings.horizon_url = "https://horizon.internal"
    settings.soroban_rpc_url = "https://rpc.internal"
    assert settings.horizon_url_for("mainnet") == "https://horizon.internal"
    assert settings.rpc_url_for("mainnet") == "https://rpc.internal"
