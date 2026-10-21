"""Soroban contract-event decoding, analysis and HTTP endpoint tests."""

from __future__ import annotations

import pytest
from fixtures.soroban_events import (
    ACCOUNT_ID,
    CONTRACT_ID,
    EVENTS,
    EVENTS_RESULT,
    MALFORMED_EVENT,
    OTHER_CONTRACT_ID,
)

from stellar_ai import analyzers
from stellar_ai.stellar import events


def test_decode_events_happy_path():
    decoded = events.decode_events(EVENTS_RESULT, contract_ids=[CONTRACT_ID])
    assert [event.event_name for event in decoded] == ["created", "funded", "released"]
    assert all(event.contract_id == CONTRACT_ID for event in decoded)
    assert all(event.decode_error is None for event in decoded)
    assert events.latest_ledger_from_result(EVENTS_RESULT) == 105

    created, funded, released = decoded
    assert created.ledger == 100
    assert created.tx_hash == "a" * 64
    assert created.topics[0] == "created"
    assert created.topics[1] == ACCOUNT_ID
    assert created.value == {
        "admin": ACCOUNT_ID,
        "name": "Token",
        "supply": 1000000,
    }

    assert funded.value == {"amount": 500}
    assert released.ledger == 101
    assert released.topics[1] == CONTRACT_ID
    assert released.value == {"amount": 1000, "recipient": ACCOUNT_ID}
    assert released.as_dict()["decoded"] is True


def test_decode_events_filters_unknown_contract():
    assert events.decode_events(EVENTS_RESULT, contract_ids=OTHER_CONTRACT_ID) == []
    assert len(events.decode_events(EVENTS_RESULT)) == len(EVENTS)


def test_decode_malformed_xdr_falls_back_to_raw():
    decoded = events.decode_event(MALFORMED_EVENT)
    assert decoded.decoded is False
    assert decoded.event_name is None
    assert decoded.topics == ["not-valid-xdr!!"]
    assert decoded.value == "not-valid-xdr!!"
    assert decoded.raw is MALFORMED_EVENT
    assert "topic[0]" in decoded.decode_error
    assert "value" in decoded.decode_error


def test_decode_events_handles_bad_results():
    assert events.extract_events(None) == []
    assert events.extract_events({"events": "nope"}) == []
    assert events.decode_events(None) == []
    assert events.latest_ledger_from_result(None) is None
    assert events.latest_ledger_from_result({"latestLedger": "bad"}) is None


def test_decode_scval_rejects_non_strings():
    with pytest.raises(ValueError, match="base64"):
        events.decode_scval(b"not-a-string")


def test_contract_id_validation():
    assert events.validate_contract_id(f"  {CONTRACT_ID}  ") == CONTRACT_ID
    assert events.is_valid_contract_id(CONTRACT_ID) is True
    assert events.is_valid_contract_id(ACCOUNT_ID) is False
    assert events.is_valid_contract_id(None) is False
    with pytest.raises(ValueError, match="invalid contract id"):
        events.validate_contract_id(ACCOUNT_ID)
    with pytest.raises(ValueError, match="invalid contract id"):
        events.validate_contract_id("")
    assert events.validate_contract_ids(None) == []
    assert events.validate_contract_ids(CONTRACT_ID) == [CONTRACT_ID]
    assert events.validate_contract_ids([CONTRACT_ID, OTHER_CONTRACT_ID]) == [
        CONTRACT_ID,
        OTHER_CONTRACT_ID,
    ]


def test_build_event_metrics_counts_and_ledger_stats():
    decoded = events.decode_events(EVENTS_RESULT, contract_ids=[CONTRACT_ID])
    metrics = analyzers.build_event_metrics(
        decoded,
        contract_id=CONTRACT_ID,
        start_ledger=100,
        latest_ledger=105,
    )
    assert metrics["total_events"] == 3
    assert metrics["decoded_events"] == 3
    assert metrics["failed_decodes"] == 0
    assert metrics["contract_id"] == CONTRACT_ID
    assert metrics["start_ledger"] == 100
    assert metrics["latest_ledger"] == 105
    assert metrics["latest_ledger_seen"] == 101
    assert metrics["event_counts"] == {"created": 1, "funded": 1, "released": 1}
    assert metrics["contract_counts"] == {CONTRACT_ID: 3}
    assert metrics["ledger_range"] == {"min": 100, "max": 101}
    assert metrics["events_per_ledger"] == {"min": 1, "max": 2, "avg": 1.5}

    summary = analyzers.summarise_events(metrics)
    assert "3 Soroban contract events" in summary
    assert "created=1" in summary
    assert "Ledger range 100-101" in summary
    assert "Failed XDR decodes: 0" in summary
    assert "Latest ledger: 105" in summary
    assert "3 Soroban contract events" in analyzers.summarise_events(decoded)


def test_build_event_metrics_handles_dicts_and_failures():
    decoded = events.decode_event(MALFORMED_EVENT)
    metrics = analyzers.build_event_metrics(
        [decoded.as_dict(), {"event_name": None, "ledger": None}],
        start_ledger=1,
    )
    assert metrics["total_events"] == 2
    assert metrics["failed_decodes"] == 1
    assert metrics["event_counts"] == {"unknown": 2}
    assert metrics["contract_counts"] == {CONTRACT_ID: 1, "unknown": 1}
    assert metrics["events_per_ledger"] == {"min": 1, "max": 1, "avg": 2.0}
    assert metrics["latest_ledger"] == 102
    assert "Failed XDR decodes: 1" in analyzers.summarise_events(metrics)


def test_summarise_events_empty():
    metrics = analyzers.build_event_metrics([], contract_id=CONTRACT_ID, start_ledger=99)
    summary = analyzers.summarise_events(metrics)
    assert summary.startswith("No Soroban contract events found")
    assert CONTRACT_ID in summary
    assert "99" in summary

    no_latest = analyzers.summarise_events(
        analyzers.build_event_metrics([], contract_id=CONTRACT_ID)
    )
    assert "Latest ledger" not in no_latest


def test_endpoint_returns_decoded_events(events_client):
    response = events_client.get(
        f"/api/v1/contracts/{CONTRACT_ID}/events",
        params={"start_ledger": 100, "limit": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contract_id"] == CONTRACT_ID
    assert body["start_ledger"] == 100
    assert body["latest_ledger"] == 105
    assert len(body["events"]) == 3
    assert body["events"][0]["event_name"] == "created"
    assert body["events"][0]["value"]["name"] == "Token"
    assert body["events"][0]["decoded"] is True
    assert "3 Soroban contract events" in body["summary"]


def test_endpoint_unknown_contract_filter_is_empty(client):
    response = client.get(
        f"/api/v1/contracts/{OTHER_CONTRACT_ID}/events",
        params={"start_ledger": 100},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["contract_id"] == OTHER_CONTRACT_ID
    assert body["events"] == []
    assert "No Soroban contract events" in body["summary"]


def test_endpoint_survives_malformed_xdr(malformed_events_client):
    response = malformed_events_client.get(
        f"/api/v1/contracts/{CONTRACT_ID}/events",
        params={"start_ledger": 100},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["events"][0]["decoded"] is False
    assert body["events"][0]["decode_error"]
    assert body["events"][0]["raw"]["value"] == "not-valid-xdr!!"


def test_endpoint_rejects_invalid_params(events_client):
    base = f"/api/v1/contracts/{CONTRACT_ID}/events"
    assert events_client.get(f"/api/v1/contracts/{ACCOUNT_ID}/events").status_code == 400
    assert events_client.get(base).status_code == 400
    assert events_client.get(base, params={"start_ledger": 0}).status_code == 400
    assert events_client.get(base, params={"start_ledger": "abc"}).status_code == 400
    assert events_client.get(base, params={"start_ledger": 100, "limit": 0}).status_code == 400
    assert events_client.get(base, params={"start_ledger": 100, "limit": 201}).status_code == 400
    assert events_client.get(base, params={"start_ledger": 100, "limit": "abc"}).status_code == 400


def test_endpoint_rpc_error_is_502(events_error_client):
    response = events_error_client.get(
        f"/api/v1/contracts/{CONTRACT_ID}/events",
        params={"start_ledger": 100},
    )
    assert response.status_code == 502


def test_chat_uses_contract_event_context(events_client, provider):
    response = events_client.post(
        "/api/v1/chat",
        json={
            "message": "What happened?",
            "contract_id": CONTRACT_ID,
            "start_ledger": 100,
        },
    )
    assert response.status_code == 200
    assert provider.prompts
    assert "3 Soroban contract events" in provider.prompts[0]
    assert "What happened?" in provider.prompts[0]


def test_chat_contract_defaults_start_ledger(events_client, provider):
    response = events_client.post(
        "/api/v1/chat",
        json={"message": "Any events?", "contract_id": CONTRACT_ID},
    )
    assert response.status_code == 200
    assert provider.prompts


def test_chat_rejects_bad_contract_id(events_client):
    response = events_client.post(
        "/api/v1/chat",
        json={"message": "Any events?", "contract_id": ACCOUNT_ID},
    )
    assert response.status_code == 400
