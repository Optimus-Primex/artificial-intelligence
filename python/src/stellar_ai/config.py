"""Runtime configuration.

All settings are environment driven with the ``STELLAR_AI_`` prefix, so the
same image can run in development, CI and production.  Well-known Horizon and
Soroban RPC endpoints are built in per network and can be overridden.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

#: Well-known public endpoints per Stellar network.
NETWORKS: dict[str, dict[str, str]] = {
    "mainnet": {
        "horizon": "https://horizon.stellar.org",
        "rpc": "https://mainnet.sorobanrpc.com",
    },
    "testnet": {
        "horizon": "https://horizon-testnet.stellar.org",
        "rpc": "https://soroban-testnet.stellar.org",
    },
    "futurenet": {
        "horizon": "https://horizon-futurenet.stellar.org",
        "rpc": "https://rpc-futurenet.stellar.org",
    },
}

DEFAULT_NETWORK = "testnet"


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="STELLAR_AI_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "stellar-ai"
    default_network: str = DEFAULT_NETWORK
    llm_provider: str = "static"
    request_timeout: float = 10.0

    # Model access. Unused by the deterministic `static` provider.
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout: float = 30.0

    # Whale-transfer detection (used by POST /api/v1/analyze).
    #: Default asset to analyse ("XLM" or "CODE:ISSUER").
    whale_asset: str = "XLM"
    #: Payments at or above this amount are reported as whale alerts.
    whale_threshold: float = 100000.0
    #: Number of recent Horizon payments to inspect per analysis.
    payment_limit: int = 50

    # Comma-separated bearer tokens. Empty disables authentication (dev mode).
    api_keys: str = ""
    # Comma-separated allowed CORS origins. Empty disables CORS.
    cors_origins: str = ""
    # "text" (human friendly) or "json" (structured).
    log_format: str = "text"

    # Optional endpoint overrides (otherwise the per-network defaults are used).
    horizon_url: str | None = None
    soroban_rpc_url: str | None = None

    @property
    def api_key_set(self) -> set[str]:
        return {key.strip() for key in self.api_keys.split(",") if key.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def resolve_network(self, network: str | None = None) -> str:
        """Validate and normalise a network name."""

        name = (network or self.default_network).strip().lower()
        if name not in NETWORKS:
            allowed = ", ".join(sorted(NETWORKS))
            raise ValueError(f"unknown network: {name!r} (expected one of: {allowed})")
        return name

    def horizon_url_for(self, network: str | None = None) -> str:
        return self.horizon_url or NETWORKS[self.resolve_network(network)]["horizon"]

    def rpc_url_for(self, network: str | None = None) -> str:
        return self.soroban_rpc_url or NETWORKS[self.resolve_network(network)]["rpc"]
