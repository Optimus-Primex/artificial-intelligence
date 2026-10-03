"""Analyzer tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from stellar_ai import analyzers


def _iso(offset_seconds: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(seconds=offset_seconds)).isoformat()


def test_ledger_lag_seconds_parses_iso():
    lag = analyzers.ledger_lag_seconds(_iso(-5))
    assert lag is not None
    assert 4 <= lag <= 30


def test_ledger_lag_seconds_parses_epoch():
    epoch = datetime.now(UTC).timestamp() - 5
    lag = analyzers.ledger_lag_seconds(epoch)
    assert lag is not None
    assert 4 <= lag <= 30


def test_ledger_lag_seconds_handles_garbage():
    assert analyzers.ledger_lag_seconds("not-a-date") is None
    assert analyzers.ledger_lag_seconds(None) is None
    assert analyzers.ledger_lag_seconds("") is None
    assert analyzers.ledger_lag_seconds(1e20) is None


def test_ledger_lag_seconds_parses_z_suffix():
    text = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lag = analyzers.ledger_lag_seconds(text)
    assert lag is not None
    assert abs(lag) < 30


def test_build_network_metrics_healthy():
    metrics = analyzers.build_network_metrics(
        network="testnet",
        horizon_url="https://h",
        rpc_url="https://r",
        horizon_ledger={"sequence": 42, "closed_at": _iso(), "protocol_version": 20},
        rpc_health={"status": "healthy"},
    )
    assert metrics["healthy"] is True
    assert metrics["latest_ledger"] == 42
    assert metrics["rpc_health"] == "healthy"


def test_build_network_metrics_stale_ledger_is_unhealthy():
    metrics = analyzers.build_network_metrics(
        network="testnet",
        horizon_url="https://h",
        rpc_url="https://r",
        horizon_ledger={"sequence": 1, "closed_at": _iso(-600)},
        rpc_health={"status": "healthy"},
    )
    assert metrics["healthy"] is False


def test_build_network_metrics_unhealthy_rpc():
    metrics = analyzers.build_network_metrics(
        network="testnet",
        horizon_url="https://h",
        rpc_url="https://r",
        horizon_ledger={"sequence": 1, "closed_at": _iso()},
        rpc_health={"status": "unhealthy"},
    )
    assert metrics["healthy"] is False


def test_summarise_mentions_network_and_state():
    text = analyzers.summarise(
        {
            "network": "testnet",
            "healthy": True,
            "latest_ledger": 10,
            "ledger_lag_seconds": 1.0,
            "rpc_health": "healthy",
        }
    )
    assert "testnet" in text
    assert "healthy" in text
    assert "10" in text
