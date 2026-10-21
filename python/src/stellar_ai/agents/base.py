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
    ):
        self.horizon = horizon
        self.soroban = soroban
        self.provider = provider

    def collect_metrics(self, network: str) -> dict:
        ledger = self.horizon.latest_ledger()
        health = self.soroban.get_health()
        rpc_ledger = self.soroban.latest_ledger()
        return analyzers.build_network_metrics(
            network=network,
            horizon_url=self.horizon.base_url,
            rpc_url=self.soroban.url,
            horizon_ledger=ledger,
            rpc_health=health,
            rpc_ledger=rpc_ledger,
        )

    def answer(self, question: str, network: str) -> AgentResult:
        metrics = self.collect_metrics(network)
        prompt = f"{analyzers.summarise(metrics)}\n\nQuestion: {question.strip()}"
        return AgentResult(answer=self.provider.complete(prompt), metrics=metrics)
