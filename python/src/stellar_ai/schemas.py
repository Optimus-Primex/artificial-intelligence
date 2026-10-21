"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NetworkStatus(BaseModel):
    """Structured snapshot of a Stellar network's health."""

    network: str
    healthy: bool
    latest_ledger: int | None = None
    ledger_lag_seconds: float | None = None
    protocol_version: int | None = None
    rpc_health: str | None = None
    horizon_url: str | None = None
    rpc_url: str | None = None


class AnalyzeRequest(BaseModel):
    network: str | None = None


class AnalyzeResponse(BaseModel):
    summary: str
    metrics: NetworkStatus
    provider: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    network: str | None = None
    contract_id: str | None = None
    start_ledger: int | None = None
    event_limit: int = Field(default=50, ge=1, le=200)


class ChatResponse(BaseModel):
    answer: str
    metrics: NetworkStatus
    provider: str


class ContractEvent(BaseModel):
    """Decoded Soroban contract event, with a raw fallback for bad XDR."""

    event_name: str | None = None
    contract_id: str | None = None
    ledger: int | None = None
    tx_hash: str | None = None
    topics: list[Any] = Field(default_factory=list)
    value: Any = None
    decoded: bool = True
    decode_error: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ContractEventsResponse(BaseModel):
    contract_id: str
    start_ledger: int
    latest_ledger: int | None = None
    summary: str
    events: list[ContractEvent] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    app: str
    provider: str
