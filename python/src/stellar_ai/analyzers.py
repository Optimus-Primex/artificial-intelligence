"""Deterministic analysis helpers.

These functions have no I/O: they turn fetched Stellar/Soroban data into
metrics and human-readable summaries. Keeping them pure makes the AI layer
testable and the LLM prompt grounded in facts rather than raw JSON.
"""

from __future__ import annotations

from collections import Counter
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
    rpc_ledger: dict | None = None,
    max_lag_seconds: float = DEFAULT_MAX_LEDGER_LAG,
) -> dict:
    """Combine Horizon ledger, Soroban health and Soroban ledger data."""

    ledger = horizon_ledger or {}
    lag = ledger_lag_seconds(ledger.get("closed_at"))
    rpc_status = (rpc_health or {}).get("status")
    rpc_status_text = rpc_status.strip().lower() if isinstance(rpc_status, str) else None

    lag_ok = lag is not None and lag <= max_lag_seconds
    # A missing or unknown status is not evidence of health.
    rpc_ok = rpc_status_text == "healthy"
    healthy = bool(lag_ok and rpc_ok)

    return {
        "network": network,
        "healthy": healthy,
        "latest_ledger": ledger.get("sequence"),
        "ledger_lag_seconds": lag,
        "protocol_version": ledger.get("protocol_version")
        or (rpc_ledger or {}).get("protocolVersion")
        or (rpc_health or {}).get("protocolVersion"),
        "rpc_health": rpc_status_text,
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


def _event_field(event, name, default=None):
    if isinstance(event, dict):
        return event.get(name, default)
    return getattr(event, name, default)


def build_event_metrics(
    events,
    *,
    contract_id: str | None = None,
    start_ledger: int | None = None,
    latest_ledger: int | None = None,
) -> dict:
    """Compute deterministic metrics over decoded Soroban contract events."""

    items = list(events or [])
    total = len(items)
    event_counts: Counter[str] = Counter()
    contract_counts: Counter[str] = Counter()
    ledger_counts: Counter[int] = Counter()
    failed_decodes = 0

    for event in items:
        if _event_field(event, "decode_error"):
            failed_decodes += 1
        event_counts[_event_field(event, "event_name") or "unknown"] += 1
        contract_counts[_event_field(event, "contract_id") or "unknown"] += 1
        ledger = _event_field(event, "ledger")
        if isinstance(ledger, int) and not isinstance(ledger, bool):
            ledger_counts[ledger] += 1

    latest_seen = max(ledger_counts) if ledger_counts else None
    if latest_ledger is None:
        latest_ledger = latest_seen

    if ledger_counts:
        ledger_range = {"min": min(ledger_counts), "max": max(ledger_counts)}
        per_ledger = {
            "min": min(ledger_counts.values()),
            "max": max(ledger_counts.values()),
            "avg": round(total / len(ledger_counts), 2),
        }
    else:
        ledger_range = {"min": None, "max": None}
        per_ledger = {"min": None, "max": None, "avg": None}

    return {
        "contract_id": contract_id,
        "start_ledger": start_ledger,
        "latest_ledger": latest_ledger,
        "latest_ledger_seen": latest_seen,
        "total_events": total,
        "decoded_events": total - failed_decodes,
        "failed_decodes": failed_decodes,
        "event_counts": dict(sorted(event_counts.items())),
        "contract_counts": dict(sorted(contract_counts.items())),
        "ledger_range": ledger_range,
        "events_per_ledger": per_ledger,
    }


def summarise_events(metrics) -> str:
    """Render contract-event metrics as a short, factual LLM-friendly summary.

    Accepts either a metrics dict from :func:`build_event_metrics` or a list of
    decoded events (which is converted to metrics first).
    """

    if not isinstance(metrics, dict):
        metrics = build_event_metrics(metrics)

    total = metrics.get("total_events") or 0
    contract = metrics.get("contract_id")
    scope = f" for contract {contract}" if contract else ""
    start = metrics.get("start_ledger")
    latest = metrics.get("latest_ledger")

    if total == 0:
        window = f" from ledger {start}" if start is not None else ""
        tail = f" Latest ledger: {latest}." if latest is not None else ""
        return f"No Soroban contract events found{scope}{window}.{tail}"

    noun = "event" if total == 1 else "events"
    parts = [f"Found {total} Soroban contract {noun}{scope}"]
    if start is not None:
        parts[0] += f" from ledger {start}"
    parts[0] += "."

    ledger_range = metrics.get("ledger_range") or {}
    min_ledger = ledger_range.get("min")
    max_ledger = ledger_range.get("max")
    if min_ledger is not None:
        parts.append(f"Ledger range {min_ledger}-{max_ledger}.")

    per_ledger = metrics.get("events_per_ledger") or {}
    if per_ledger.get("avg") is not None:
        parts.append(
            "Events per ledger: "
            f"min {per_ledger['min']}, max {per_ledger['max']}, avg {per_ledger['avg']}."
        )

    event_counts = metrics.get("event_counts") or {}
    if event_counts:
        rendered = ", ".join(f"{name}={count}" for name, count in event_counts.items())
        parts.append(f"Event types: {rendered}.")

    parts.append(f"Failed XDR decodes: {metrics.get('failed_decodes', 0)}.")
    if latest is not None:
        parts.append(f"Latest ledger: {latest}.")
    return " ".join(parts)
