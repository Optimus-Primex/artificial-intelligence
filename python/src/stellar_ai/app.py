"""FastAPI application for Stellar AI.

Collaborators (Stellar clients, LLM provider) are constructed here and injected
into the agent, so tests can pass fakes and run entirely offline.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from . import analyzers
from .agents.base import StellarInsightAgent
from .config import Settings
from .llm.provider import build_provider
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    NetworkStatus,
)
from .stellar import HorizonClient, SorobanRpcClient, StellarClientError


def create_app(
    settings: Settings | None = None,
    horizon_factory=None,
    rpc_factory=None,
    provider=None,
) -> FastAPI:
    """Build the FastAPI application, allowing collaborators to be overridden."""

    settings = settings or Settings()
    provider = provider or build_provider(settings.llm_provider)
    horizon_factory = horizon_factory or (
        lambda url: HorizonClient(url, timeout=settings.request_timeout)
    )
    rpc_factory = rpc_factory or (
        lambda url: SorobanRpcClient(url, timeout=settings.request_timeout)
    )

    app = FastAPI(title="Stellar AI", version="0.1.0")

    def build_agent(network: str | None) -> tuple[StellarInsightAgent, str]:
        try:
            net = settings.resolve_network(network)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        agent = StellarInsightAgent(
            horizon_factory(settings.horizon_url_for(net)),
            rpc_factory(settings.rpc_url_for(net)),
            provider,
        )
        return agent, net

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", app=settings.app_name, provider=provider.name)

    @app.get("/api/v1/network/status", response_model=NetworkStatus)
    def network_status(network: str | None = Query(default=None)) -> NetworkStatus:
        agent, net = build_agent(network)
        try:
            metrics = agent.collect_metrics(net)
        except StellarClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return NetworkStatus(**metrics)

    @app.post("/api/v1/analyze", response_model=AnalyzeResponse)
    def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
        agent, net = build_agent(request.network)
        try:
            metrics = agent.collect_metrics(net)
        except StellarClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return AnalyzeResponse(
            summary=analyzers.summarise(metrics),
            metrics=NetworkStatus(**metrics),
            provider=provider.name,
        )

    @app.post("/api/v1/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        agent, net = build_agent(request.network)
        try:
            result = agent.answer(request.message, net)
        except StellarClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return ChatResponse(
            answer=result.answer,
            metrics=NetworkStatus(**result.metrics),
            provider=provider.name,
        )

    return app


app = create_app()
