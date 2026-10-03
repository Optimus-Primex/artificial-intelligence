"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

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


class ChatResponse(BaseModel):
    answer: str
    metrics: NetworkStatus
    provider: str


class HealthResponse(BaseModel):
    status: str
    app: str
    provider: str
