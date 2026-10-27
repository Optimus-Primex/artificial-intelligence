"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnomalyFlag(BaseModel):
    """A deterministic anomaly found in a recent ledger series."""

    code: str
    severity: str
    message: str
    ledger: int | None = None
    previous_ledger: int | None = None
    value: float | None = None
    threshold: float | None = None


class LedgerSeries(BaseModel):
    """Summary of close-time intervals for recent ledgers."""

    samples: int = 0
    latest_ledger: int | None = None
    latest_lag_seconds: float | None = None
    close_intervals: dict[str, float | None] = Field(default_factory=dict)
    anomalous: bool = False


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
    ledger_series: LedgerSeries | None = None
    flags: list[AnomalyFlag] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    network: str | None = None
    #: Asset to scan for whale transfers ("XLM" or "CODE:ISSUER").
    asset: str | None = None
    #: Override the configured whale threshold for this request.
    whale_threshold: float | None = Field(default=None, gt=0)
    #: Number of recent payments to inspect (defaults to the server setting).
    payment_limit: int | None = Field(default=None, ge=1, le=200)


class WhaleAlert(BaseModel):
    """A single payment at or above the configured threshold."""

    amount: float
    asset: str
    from_account: str | None = None
    to_account: str | None = None
    transaction_hash: str | None = None
    created_at: str | None = None
    ledger: int | None = None


class PaymentAnalysis(BaseModel):
    """Summary of the payments scanned for one network/asset."""

    network: str
    asset: str
    threshold: float
    limit: int
    payments_scanned: int
    matching_payments: int
    skipped_payments: int = 0
    whale_count: int
    total_volume: float
    largest_payment: WhaleAlert | None = None
    alerts: list[WhaleAlert] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    summary: str
    metrics: NetworkStatus
    provider: str
    payments: PaymentAnalysis | None = None
    alerts: list[WhaleAlert] = Field(default_factory=list)
    flags: list[AnomalyFlag] = Field(default_factory=list)


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
