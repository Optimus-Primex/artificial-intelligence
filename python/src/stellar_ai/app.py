"""FastAPI application for Stellar AI.

Collaborators (Stellar clients, LLM provider) are constructed here and injected
into the agent, so tests can pass fakes and run entirely offline.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import analyzers
from .agents.base import StellarInsightAgent
from .config import Settings
from .errors import install_error_handlers
from .llm.provider import build_provider
from .logging_config import configure_logging
from .middleware import install_request_middleware
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
    configure_logging(settings.log_format)

    horizon_factory = horizon_factory or (
        lambda url: HorizonClient(url, timeout=settings.request_timeout)
    )
    rpc_factory = rpc_factory or (
        lambda url: SorobanRpcClient(url, timeout=settings.request_timeout)
    )

    app = FastAPI(title="Stellar AI", version="0.1.0")

    install_request_middleware(app)
    install_error_handlers(app)

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )

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

    def require_api_key(authorization: str | None = Header(default=None)) -> None:
        """Enforce a bearer key when ``STELLAR_AI_API_KEYS`` is configured."""

        keys = settings.api_key_set
        if not keys:
            return  # authentication disabled in development
        token = None
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        if not token or token not in keys:
            raise HTTPException(
                status_code=401,
                detail="invalid or missing API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """Liveness probe (unauthenticated)."""

        return HealthResponse(status="ok", app=settings.app_name, provider=provider.name)

    @app.get("/ready")
    def ready():
        """Readiness probe: verifies Horizon and Soroban RPC are reachable."""

        agent, net = build_agent(None)
        try:
            agent.horizon.latest_ledger()
            agent.soroban.get_health()
        except StellarClientError as exc:
            return JSONResponse(
                status_code=503, content={"status": "unavailable", "detail": str(exc)}
            )
        return {"status": "ready", "network": net}

    api = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])

    @api.get("/network/status", response_model=NetworkStatus)
    def network_status(network: str | None = Query(default=None)) -> NetworkStatus:
        agent, net = build_agent(network)
        try:
            metrics = agent.collect_metrics(net)
        except StellarClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return NetworkStatus(**metrics)

    @api.post("/analyze", response_model=AnalyzeResponse)
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

    @api.post("/chat", response_model=ChatResponse)
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

    app.include_router(api)
    return app


app = create_app()
