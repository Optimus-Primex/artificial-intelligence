"""Request-id / middleware tests."""

from __future__ import annotations

import logging

from stellar_ai.logging_config import JsonFormatter


def test_response_gets_a_request_id(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")


def test_incoming_request_id_is_preserved(client):
    response = client.get("/health", headers={"X-Request-ID": "trace-123"})
    assert response.headers["X-Request-ID"] == "trace-123"


def test_request_id_present_on_errors(client):
    response = client.get("/api/v1/network/status", params={"network": "regtest"})
    assert response.status_code == 400
    assert response.headers.get("X-Request-ID")


def test_json_formatter_includes_extra_fields():
    record = logging.LogRecord(
        name="stellar_ai.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request",
        args=(),
        exc_info=None,
    )
    record.request_id = "abc"
    record.status = 200
    payload = JsonFormatter().format(record)
    assert '"request_id": "abc"' in payload
    assert '"status": 200' in payload
    assert '"message": "request"' in payload
