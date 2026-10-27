"""The Stellar insight agent.

It grounds LLM answers in live network metrics rather than raw JSON: fetch
Horizon + Soroban data, derive metrics with :mod:`stellar_ai.analyzers`, then
ask the configured provider.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import analyzers
from ..llm.provider import LLMProvider
from ..stellar.horizon import HorizonClient
from ..stellar.soroban import SorobanRpcClient


@dataclass
class AgentResult:
    answer: str
    metrics: dict


class StellarInsightAgent:
    def __init__(
        self,
        horizon: HorizonClient,
        soroban: SorobanRpcClient,
        provider: LLMProvider,
        *,
        max_ledger_lag_seconds: float = analyzers.DEFAULT_MAX_LEDGER_LAG,
        max_close_interval_seconds: float = analyzers.DEFAULT_MAX_CLOSE_INTERVAL,
        close_interval_outlier_factor: float = analyzers.DEFAULT_CLOSE_INTERVAL_FACTOR,
        ledger_history_limit: int = 20,
    ):
        self.horizon = horizon
        self.soroban = soroban
        self.provider = provider
        self.max_ledger_lag_seconds = max_ledger_lag_seconds
        self.max_close_interval_seconds = max_close_interval_seconds
        self.close_interval_outlier_factor = close_interval_outlier_factor
        self.ledger_history_limit = max(1, int(ledger_history_limit))

    def collect_metrics(self, network: str) -> dict:
        recent = self.horizon.recent_ledgers(self.ledger_history_limit)
        ledger = recent[0] if recent else self.horizon.latest_ledger()
        health = self.soroban.get_health()
        rpc_ledger = self.soroban.latest_ledger()
        return analyzers.build_network_metrics(
            network=network,
            horizon_url=self.horizon.base_url,
            rpc_url=self.soroban.url,
            horizon_ledger=ledger,
            rpc_health=health,
            rpc_ledger=rpc_ledger,
            recent_ledgers=recent,
            max_lag_seconds=self.max_ledger_lag_seconds,
            max_close_interval_seconds=self.max_close_interval_seconds,
            close_interval_outlier_factor=self.close_interval_outlier_factor,
        )

    def collect_payments(
        self,
        network: str,
        *,
        asset: str | None = None,
        threshold: float = analyzers.DEFAULT_WHALE_THRESHOLD,
        limit: int = 50,
    ) -> dict:
        """Scan recent Horizon payments and flag whale-sized transfers."""

        payments = self.horizon.recent_payments(limit=limit)
        return analyzers.build_payment_metrics(
            payments,
            network=network,
            asset=asset or analyzers.DEFAULT_WHALE_ASSET,
            threshold=threshold,
            limit=limit,
        )

    def answer(
        self,
        question: str,
        network: str,
        context: str | None = None,
    ) -> AgentResult:
        metrics = self.collect_metrics(network)
        prompt = analyzers.summarise(metrics)
        if context:
            prompt = f"{prompt}\n{context}"
        prompt = f"{prompt}\n\nQuestion: {question.strip()}"
        return AgentResult(answer=self.provider.complete(prompt), metrics=metrics)
