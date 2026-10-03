"""Deterministic analysis helpers.

These functions have no I/O: they turn fetched Stellar/Soroban data into
metrics and human-readable summaries. Keeping them pure makes the AI layer
testable and the LLM prompt grounded in facts rather than raw JSON.
"""

from __future__ import annotations

from datetime import UTC, datetime

DEFAULT_MAX_LEDGER_LAG = 30.0


def parse_timestamp(value) -> datetime | None:
    """Parse an ISO-8601 string or unix epoch into a naive UTC datetime."""

    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=UTC).replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.fromtimestamp(float(text), tz=UTC).replace(tzinfo=None)
            except (OverflowError, OSError, ValueError):
                return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed
    return None


def ledger_lag_seconds(closed_at, now: datetime | None = None) -> float | None:
    """Seconds between a ledger close time and ``now`` (``None`` if unparseable)."""

    closed = parse_timestamp(closed_at)
    if closed is None:
        return None
    reference = now or datetime.now(UTC).replace(tzinfo=None)
    return round((reference - closed).total_seconds(), 2)


def build_network_metrics(
    *,
    network: str,
    horizon_url: str | None,
    rpc_url: str | None,
    horizon_ledger: dict | None,
    rpc_health: dict | None,
    max_lag_seconds: float = DEFAULT_MAX_LEDGER_LAG,
) -> dict:
    """Combine a Horizon ledger record and a Soroban RPC health into metrics."""

    ledger = horizon_ledger or {}
    lag = ledger_lag_seconds(ledger.get("closed_at"))
    rpc_status = (rpc_health or {}).get("status")

    lag_ok = lag is not None and lag <= max_lag_seconds
    rpc_ok = rpc_status in (None, "healthy")
    healthy = bool(lag_ok and rpc_ok)

    return {
        "network": network,
        "healthy": healthy,
        "latest_ledger": ledger.get("sequence"),
        "ledger_lag_seconds": lag,
        "protocol_version": ledger.get("protocol_version")
        or (rpc_health or {}).get("protocolVersion"),
        "rpc_health": rpc_status,
        "horizon_url": horizon_url,
        "rpc_url": rpc_url,
    }


def summarise(metrics: dict) -> str:
    """Render metrics as a short, LLM-friendly summary."""

    network = metrics.get("network", "unknown")
    state = "healthy" if metrics.get("healthy") else "degraded"
    lines = [f"Stellar {network} is {state}."]
    if metrics.get("latest_ledger") is not None:
        lines.append(f"Latest ledger: {metrics['latest_ledger']}.")
    if metrics.get("ledger_lag_seconds") is not None:
        lines.append(f"Ledger close lag: {metrics['ledger_lag_seconds']}s.")
    if metrics.get("rpc_health"):
        lines.append(f"Soroban RPC health: {metrics['rpc_health']}.")
    return " ".join(lines)
