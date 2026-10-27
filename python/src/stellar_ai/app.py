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
from .llm.provider import LLMError, build_provider
from .logging_config import configure_logging
from .middleware import install_request_middleware
from .rate_limit import install_rate_limit_middleware
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    ContractEvent,
    ContractEventsResponse,
    HealthResponse,
    NetworkStatus,
)
from .stellar import HorizonClient, SorobanRpcClient, StellarClientError
from .stellar import events as stellar_events


def create_app(
    settings: Settings | None = None,
    horizon_factory=None,
    rpc_factory=None,
    provider=None,
) -> FastAPI:
    """Build the FastAPI application, allowing collaborators to be overridden."""

    settings = settings or Settings()
    provider = provider or build_provider(
        settings.llm_provider,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout,
    )
    configure_logging(settings.log_format)

    horizon_factory = horizon_factory or (
        lambda url: HorizonClient(url, timeout=settings.request_timeout)
    )
    rpc_factory = rpc_factory or (
        lambda url: SorobanRpcClient(url, timeout=settings.request_timeout)
    )

    app = FastAPI(title="Stellar AI", version="0.1.0")

    # Add the rate limiter first so the request-id/logging middleware wraps it
    # and 429 responses still carry X-Request-ID.
    install_rate_limit_middleware(app, settings)
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
            max_ledger_lag_seconds=settings.max_ledger_lag_seconds,
            max_close_interval_seconds=settings.max_close_interval_seconds,
            close_interval_outlier_factor=settings.close_interval_outlier_factor,
            ledger_history_limit=settings.ledger_history_limit,
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

    def decode_contract_events(agent, contract_id: str, start_ledger: int, limit: int):
        result = agent.soroban.get_events(start_ledger, [contract_id], limit)
        decoded = stellar_events.decode_events(result, [contract_id])
        metrics = analyzers.build_event_metrics(
            decoded,
            contract_id=contract_id,
            start_ledger=start_ledger,
            latest_ledger=stellar_events.latest_ledger_from_result(result),
        )
        return decoded, metrics

    api = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])

    @api.get("/network/status", response_model=NetworkStatus)
    def network_status(network: str | None = Query(default=None)) -> NetworkStatus:
        agent, net = build_agent(network)
        try:
            metrics = agent.collect_metrics(net)
        except StellarClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return NetworkStatus(**metrics)

    @api.get("/contracts/{contract_id}/events", response_model=ContractEventsResponse)
    def contract_events(
        contract_id: str,
        start_ledger: str | None = Query(
            default=None, description="Starting ledger (positive integer)."
        ),
        limit: str = Query(default="100", description="Maximum events to return (1-200)."),
        network: str | None = Query(default=None),
    ) -> ContractEventsResponse:
        try:
            contract = stellar_events.validate_contract_id(contract_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        try:
            start = int(start_ledger) if start_ledger is not None else None
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400, detail="start_ledger must be a positive integer"
            ) from exc
        if start is None or start < 1:
            raise HTTPException(status_code=400, detail="start_ledger must be a positive integer")

        try:
            parsed_limit = int(limit)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 200") from exc
        if not 1 <= parsed_limit <= 200:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 200")

        agent, _net = build_agent(network)
        try:
            decoded, metrics = decode_contract_events(agent, contract, start, parsed_limit)
        except StellarClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return ContractEventsResponse(
            contract_id=contract,
            start_ledger=start,
            latest_ledger=metrics["latest_ledger"],
            summary=analyzers.summarise_events(metrics),
            events=[ContractEvent(**event.as_dict()) for event in decoded],
        )

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
            flags=metrics.get("flags", []),
        )

    @api.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        agent, net = build_agent(request.network)
        context = None
        try:
            if request.contract_id:
                try:
                    contract = stellar_events.validate_contract_id(request.contract_id)
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc

                start_ledger = request.start_ledger
                if start_ledger is None:
                    latest = agent.soroban.latest_ledger() or {}
                    sequence = latest.get("sequence") if isinstance(latest, dict) else None
                    start_ledger = max(1, sequence - 100) if isinstance(sequence, int) else 1
                if start_ledger < 1:
                    raise HTTPException(
                        status_code=400,
                        detail="start_ledger must be a positive integer",
                    )

                _decoded, event_metrics = decode_contract_events(
                    agent, contract, start_ledger, request.event_limit
                )
                context = analyzers.summarise_events(event_metrics)

            result = agent.answer(request.message, net, context=context)
        except StellarClientError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return ChatResponse(
            answer=result.answer,
            metrics=NetworkStatus(**result.metrics),
            provider=provider.name,
        )

    app.include_router(api)
    return app


app = create_app()
