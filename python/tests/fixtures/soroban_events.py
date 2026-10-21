"""Real Soroban XDR fixtures generated offline with stellar-sdk 16.1.0.

The base64 strings are stable ``SCVal`` payloads for the topic/value fields
returned by the Soroban RPC ``getEvents`` method.
"""

from __future__ import annotations

CONTRACT_ID = "CAAACAQDAQCQMBYIBEFAWDANBYHRAEISCMKBKFQXDAMRUGY4DUPB6N4O"
OTHER_CONTRACT_ID = "CAAQCAIBAEAQCAIBAEAQCAIBAEAQCAIBAEAQCAIBAEAQCAIBAEAQC526"
ACCOUNT_ID = "GAAACAQDAQCQMBYIBEFAWDANBYHRAEISCMKBKFQXDAMRUGY4DUPB7JZX"

TOPIC_CREATED = "AAAADwAAAAdjcmVhdGVkAA=="
TOPIC_FUNDED = "AAAADwAAAAZmdW5kZWQAAA=="
TOPIC_RELEASED = "AAAADwAAAAhyZWxlYXNlZA=="
TOPIC_ACCOUNT = "AAAAEgAAAAAAAAAAAAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
TOPIC_CONTRACT = "AAAAEgAAAAEAAQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHw=="

VALUE_CREATED = (
    "AAAAEQAAAAEAAAADAAAADwAAAAVhZG1pbgAAAAAAABIAAAAAAAAAAAABAgMEBQYHCAkKCwwNDg8Q"
    "ERITFBUWFxgZGhscHR4fAAAADwAAAARuYW1lAAAADgAAAAVUb2tlbgAAAAAAAA8AAAAGc3VwcGx5"
    "AAAAAAAFAAAAAAAPQkA="
)
VALUE_FUNDED = "AAAAEQAAAAEAAAABAAAADwAAAAZhbW91bnQAAAAAAAUAAAAAAAAB9A=="
VALUE_RELEASED = (
    "AAAAEQAAAAEAAAACAAAADwAAAAZhbW91bnQAAAAAAAUAAAAAAAAD6AAAAA8AAAAJcmVjaXBpZW50"
    "AAAAAAAAEgAAAAAAAAAAAAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
)
INVALID_XDR = "not-valid-xdr!!"


def event(
    *,
    name: str,
    topic: str,
    value: str,
    ledger: int,
    tx_hash: str,
    contract_id: str = CONTRACT_ID,
    extra_topic: str | None = None,
) -> dict:
    topics = [topic]
    if extra_topic:
        topics.append(extra_topic)
    return {
        "type": "contract",
        "ledger": ledger,
        "ledgerClosedAt": "2026-01-01T00:00:00Z",
        "contractId": contract_id,
        "id": f"{ledger:010d}-0000000001",
        "pagingToken": f"{ledger:010d}-0000000001",
        "inSuccessfulContractCall": True,
        "txHash": tx_hash,
        "topic": topics,
        "value": value,
        "_fixture_name": name,
    }


CREATED_EVENT = event(
    name="created",
    topic=TOPIC_CREATED,
    value=VALUE_CREATED,
    ledger=100,
    tx_hash="a" * 64,
    extra_topic=TOPIC_ACCOUNT,
)
FUNDED_EVENT = event(
    name="funded",
    topic=TOPIC_FUNDED,
    value=VALUE_FUNDED,
    ledger=101,
    tx_hash="b" * 64,
    extra_topic=TOPIC_ACCOUNT,
)
RELEASED_EVENT = event(
    name="released",
    topic=TOPIC_RELEASED,
    value=VALUE_RELEASED,
    ledger=101,
    tx_hash="c" * 64,
    extra_topic=TOPIC_CONTRACT,
)
MALFORMED_EVENT = event(
    name="malformed",
    topic=INVALID_XDR,
    value=INVALID_XDR,
    ledger=102,
    tx_hash="d" * 64,
)

EVENTS = [CREATED_EVENT, FUNDED_EVENT, RELEASED_EVENT]
EVENTS_RESULT = {"events": EVENTS, "latestLedger": 105, "oldestLedger": 90}
