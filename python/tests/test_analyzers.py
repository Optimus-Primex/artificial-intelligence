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


def test_missing_rpc_status_is_unhealthy():
    metrics = analyzers.build_network_metrics(
        network="testnet",
        horizon_url="https://h",
        rpc_url="https://r",
        horizon_ledger={"sequence": 1, "closed_at": _iso()},
        rpc_health=None,
    )
    assert metrics["healthy"] is False
    assert metrics["rpc_health"] is None


def test_protocol_version_falls_back_to_rpc_ledger():
    metrics = analyzers.build_network_metrics(
        network="testnet",
        horizon_url="https://h",
        rpc_url="https://r",
        horizon_ledger={"sequence": 1, "closed_at": _iso()},
        rpc_health={"status": "healthy"},
        rpc_ledger={"sequence": 99, "protocolVersion": 21},
    )
    assert metrics["protocol_version"] == 21


# -- whale transfers -------------------------------------------------------
def _payment(amount, asset_type="native", **overrides):
    record = {
        "type": "payment",
        "asset_type": asset_type,
        "amount": str(amount),
        "from": "GFROM",
        "to": "GTO",
        "transaction_hash": f"tx-{amount}",
        "created_at": _iso(),
        "transaction_successful": True,
    }
    record.update(overrides)
    return record


def test_payment_metrics_flags_at_or_above_threshold():
    metrics = analyzers.build_payment_metrics(
        [_payment("99"), _payment("100"), _payment("250")],
        network="testnet",
        asset="XLM",
        threshold=100,
    )
    assert metrics["payments_scanned"] == 3
    assert metrics["matching_payments"] == 3
    assert metrics["whale_count"] == 2
    assert [alert["amount"] for alert in metrics["alerts"]] == [250.0, 100.0]
    assert metrics["largest_payment"]["amount"] == 250.0
    assert metrics["total_volume"] == 449.0


def test_payment_metrics_below_threshold_has_no_alerts():
    metrics = analyzers.build_payment_metrics(
        [_payment("10"), _payment("20")],
        network="testnet",
        threshold=100,
    )
    assert metrics["whale_count"] == 0
    assert metrics["alerts"] == []
    assert metrics["largest_payment"]["amount"] == 20.0


def test_payment_metrics_filters_by_asset():
    native = _payment("500")
    usdc = _payment(
        "750",
        asset_type="credit_alphanum4",
        asset_code="USDC",
        asset_issuer="GISSUER",
    )
    metrics = analyzers.build_payment_metrics(
        [native, usdc],
        network="testnet",
        asset="USDC:GISSUER",
        threshold=100,
    )
    assert metrics["matching_payments"] == 1
    assert metrics["alerts"][0]["amount"] == 750.0
    assert metrics["alerts"][0]["asset"] == "USDC:GISSUER"


def test_payment_metrics_handles_bad_amounts_and_failed_txs():
    metrics = analyzers.build_payment_metrics(
        [
            _payment("not-a-number"),
            _payment("500", transaction_successful=False),
            _payment("5"),
            {"type": "create_account"},
        ],
        network="testnet",
        threshold=100,
    )
    assert metrics["payments_scanned"] == 4
    assert metrics["matching_payments"] == 1
    assert metrics["skipped_payments"] == 2
    assert metrics["whale_count"] == 0


def test_summarise_payments_mentions_count_and_threshold():
    metrics = analyzers.build_payment_metrics(
        [_payment("500")], network="testnet", asset="XLM", threshold=100
    )
    text = analyzers.summarise_payments(metrics)
    assert "1 whale transfer" in text
    assert "100 XLM" in text
    assert "500 XLM" in text


def test_normalise_asset():
    assert analyzers.normalise_asset(None) == "XLM"
    assert analyzers.normalise_asset("native") == "XLM"
    assert analyzers.normalise_asset("usdc:gis") == "USDC:gis"
    assert analyzers.normalise_asset("usdc") == "USDC"


# -- ledger series anomaly detection ---------------------------------------
NOW = datetime(2026, 10, 25, 12, 0, 0)


def _ledger(sequence: int, offset_seconds: int) -> dict:
    closed = NOW + timedelta(seconds=offset_seconds)
    return {"sequence": sequence, "closed_at": closed.isoformat()}


def test_ledger_series_normal_is_not_anomalous():
    ledgers = [_ledger(100 - index, -5 * index) for index in range(6)]

    series = analyzers.analyze_ledger_series(ledgers, now=NOW)

    assert series["samples"] == 6
    assert series["latest_ledger"] == 100
    assert series["latest_lag_seconds"] == 0
    assert series["close_intervals"]["median"] == 5
    assert series["flags"] == []
    assert series["anomalous"] is False


def test_ledger_series_flags_stale_latest_ledger():
    ledgers = [_ledger(100, -600), _ledger(99, -605), _ledger(98, -610)]

    series = analyzers.analyze_ledger_series(ledgers, now=NOW, max_lag_seconds=30)

    flags = {flag["code"]: flag for flag in series["flags"]}
    assert "ledger_lag" in flags
    assert flags["ledger_lag"]["severity"] == "critical"
    assert flags["ledger_lag"]["ledger"] == 100
    assert flags["ledger_lag"]["value"] == 600
    assert series["anomalous"] is True


def test_ledger_series_flags_close_interval_outlier():
    ledgers = [
        _ledger(100, 0),
        _ledger(99, -5),
        _ledger(98, -10),
        _ledger(97, -30),
        _ledger(96, -35),
        _ledger(95, -40),
    ]

    series = analyzers.analyze_ledger_series(
        ledgers, now=NOW, max_close_interval_seconds=30, close_interval_outlier_factor=3
    )

    flags = {flag["code"]: flag for flag in series["flags"]}
    assert "close_interval_outlier" in flags
    assert flags["close_interval_outlier"]["severity"] == "warning"
    assert flags["close_interval_outlier"]["previous_ledger"] == 97
    assert flags["close_interval_outlier"]["ledger"] == 98
    assert flags["close_interval_outlier"]["value"] == 20
    assert "stalled_ingestion" not in flags


def test_ledger_series_flags_stalled_ingestion():
    ledgers = [_ledger(100, 0), _ledger(99, -120), _ledger(98, -125)]

    series = analyzers.analyze_ledger_series(ledgers, now=NOW, max_close_interval_seconds=30)

    flags = {flag["code"]: flag for flag in series["flags"]}
    assert "stalled_ingestion" in flags
    assert flags["stalled_ingestion"]["severity"] == "critical"
    assert flags["stalled_ingestion"]["value"] == 120


def test_ledger_series_thresholds_are_configurable():
    ledgers = [_ledger(100, 0), _ledger(99, -10), _ledger(98, -20)]

    strict = analyzers.analyze_ledger_series(ledgers, now=NOW, max_close_interval_seconds=5)
    relaxed = analyzers.analyze_ledger_series(ledgers, now=NOW, max_close_interval_seconds=60)

    assert "stalled_ingestion" in {flag["code"] for flag in strict["flags"]}
    assert relaxed["flags"] == []


def test_ledger_series_ignores_unusable_records():
    ledgers = [
        _ledger(100, 0),
        {"sequence": "99", "closed_at": _iso(-5)},
        {"sequence": 98, "closed_at": "not-a-date"},
        None,
        "garbage",
        _ledger(97, -10),
    ]

    series = analyzers.analyze_ledger_series(ledgers, now=NOW)

    assert series["samples"] == 2
    assert series["flags"] == []


def test_ledger_series_flags_close_time_out_of_order():
    ledgers = [
        {"sequence": 100, "closed_at": (NOW - timedelta(seconds=20)).isoformat()},
        {"sequence": 99, "closed_at": (NOW - timedelta(seconds=5)).isoformat()},
    ]

    series = analyzers.analyze_ledger_series(ledgers, now=NOW)

    assert "close_time_out_of_order" in {flag["code"] for flag in series["flags"]}


def test_ledger_series_empty():
    series = analyzers.analyze_ledger_series([], now=NOW)

    assert series["samples"] == 0
    assert series["latest_ledger"] is None
    assert series["flags"] == []
    assert series["anomalous"] is False


def test_build_network_metrics_includes_flags():
    ledgers = [_ledger(100, -600), _ledger(99, -605), _ledger(98, -610)]

    metrics = analyzers.build_network_metrics(
        network="testnet",
        horizon_url="https://h",
        rpc_url="https://r",
        horizon_ledger=ledgers[0],
        rpc_health={"status": "healthy"},
        recent_ledgers=ledgers,
        now=NOW,
    )

    assert metrics["healthy"] is False
    assert metrics["ledger_series"]["samples"] == 3
    assert "ledger_lag" in {flag["code"] for flag in metrics["flags"]}


def test_summarise_mentions_anomalies():
    text = analyzers.summarise(
        {
            "network": "testnet",
            "healthy": False,
            "latest_ledger": 10,
            "ledger_lag_seconds": 600.0,
            "rpc_health": "healthy",
            "flags": [
                {
                    "code": "ledger_lag",
                    "severity": "critical",
                    "message": "Ledger 10 closed 600s ago (threshold 30s)",
                }
            ],
        }
    )

    assert "Anomalies:" in text
    assert "600s" in text
