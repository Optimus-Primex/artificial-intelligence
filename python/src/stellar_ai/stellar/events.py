"""Decode Soroban contract events returned by the ``getEvents`` RPC method.

The RPC returns topics and values as base64-encoded ``SCVal`` XDR strings. This
module turns them into native Python values with the official ``stellar-sdk``
helpers and never raises while decoding a single event: malformed data is
preserved as a raw fallback so the HTTP endpoint keeps working.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from stellar_sdk import Address, StrKey, scval
from stellar_sdk.xdr import SCVal


def is_valid_contract_id(value: object) -> bool:
    """Return ``True`` for a valid Soroban contract address (``C...``)."""

    if not isinstance(value, str):
        return False
    return StrKey.is_valid_contract(value.strip())


def validate_contract_id(value: object) -> str:
    """Normalise a contract id or raise ``ValueError`` for invalid input."""

    if not isinstance(value, str) or not is_valid_contract_id(value):
        raise ValueError("invalid contract id: expected a Soroban contract address (C...)")
    return value.strip()


def validate_contract_ids(values: object) -> list[str]:
    """Normalise one contract id or an iterable of contract ids."""

    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return [validate_contract_id(value) for value in values]


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _jsonable(value: Any) -> Any:
    """Convert stellar-sdk native values into JSON-serialisable values."""

    if isinstance(value, Address):
        return value.address
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex()
    if isinstance(value, SCVal):
        return value.to_json_dict()
    if isinstance(value, dict):
        return {str(_jsonable(key)): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def decode_scval(value: object) -> Any:
    """Decode a base64 ``SCVal`` XDR string into a native Python value."""

    if not isinstance(value, str):
        raise ValueError("expected a base64-encoded SCVal string")
    return _jsonable(scval.to_native(value))


def latest_ledger_from_result(result: object) -> int | None:
    """Read ``latestLedger`` from a ``getEvents`` result, if present."""

    if not isinstance(result, dict):
        return None
    return _as_int(result.get("latestLedger"))


def extract_events(result: object) -> list[dict]:
    """Return the raw event dictionaries from a ``getEvents`` result."""

    if not isinstance(result, dict):
        return []
    events = result.get("events")
    if not isinstance(events, list):
        return []
    return [event for event in events if isinstance(event, dict)]


@dataclass(frozen=True)
class DecodedEvent:
    """Typed, JSON-friendly summary of a single contract event."""

    event_name: str | None = None
    contract_id: str | None = None
    ledger: int | None = None
    tx_hash: str | None = None
    topics: list[Any] = field(default_factory=list)
    value: Any = None
    decode_error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def decoded(self) -> bool:
        return self.decode_error is None

    def as_dict(self) -> dict:
        return {
            "event_name": self.event_name,
            "contract_id": self.contract_id,
            "ledger": self.ledger,
            "tx_hash": self.tx_hash,
            "topics": self.topics,
            "value": self.value,
            "decoded": self.decoded,
            "decode_error": self.decode_error,
            "raw": self.raw,
        }


def decode_event(event: dict) -> DecodedEvent:
    """Decode one RPC event, falling back to raw values on XDR errors."""

    raw_topics = event.get("topic")
    if not isinstance(raw_topics, list):
        raw_topics = [] if raw_topics is None else [raw_topics]

    topics: list[Any] = []
    errors: list[str] = []
    event_name: str | None = None

    for index, raw_topic in enumerate(raw_topics):
        try:
            topic = decode_scval(raw_topic)
        except Exception as exc:  # noqa: BLE001 - malformed XDR must not crash
            topics.append(raw_topic)
            errors.append(f"topic[{index}]: {exc}")
            continue
        topics.append(topic)
        if index == 0 and isinstance(topic, str):
            event_name = topic

    raw_value = event.get("value")
    if raw_value is None:
        value: Any = None
    else:
        try:
            value = decode_scval(raw_value)
        except Exception as exc:  # noqa: BLE001 - malformed XDR must not crash
            value = raw_value
            errors.append(f"value: {exc}")

    return DecodedEvent(
        event_name=event_name,
        contract_id=event.get("contractId") or event.get("contract_id"),
        ledger=_as_int(event.get("ledger")),
        tx_hash=event.get("txHash") or event.get("tx_hash"),
        topics=topics,
        value=value,
        decode_error="; ".join(errors) if errors else None,
        raw=event,
    )


def decode_events(result: object, contract_ids: object = None) -> list[DecodedEvent]:
    """Decode all events in an RPC result, optionally filtering by contract."""

    wanted = set(validate_contract_ids(contract_ids))
    decoded = [decode_event(event) for event in extract_events(result)]
    if not wanted:
        return decoded
    # The RPC filter is authoritative; keep events that omit the optional
    # contractId field but drop any that explicitly name another contract.
    return [event for event in decoded if event.contract_id is None or event.contract_id in wanted]
