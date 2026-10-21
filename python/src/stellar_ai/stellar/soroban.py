"""Minimal Soroban RPC (JSON-RPC 2.0) client.

The RPC call is injectable via ``rpc_call`` so tests can run offline.
"""

from __future__ import annotations

import httpx

from .errors import StellarClientError


class SorobanRpcClient:
    def __init__(self, url: str, timeout: float = 10.0, rpc_call=None):
        self.url = url
        self.timeout = timeout
        self._rpc_call = rpc_call

    def _call(self, method: str, params: dict | None = None):
        if self._rpc_call is not None:
            return self._rpc_call(method, params)

        payload: dict = {"jsonrpc": "2.0", "id": 1, "method": method}
        if params is not None:
            payload["params"] = params
        try:
            response = httpx.post(self.url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            raise StellarClientError(str(exc)) from exc
        except ValueError as exc:
            raise StellarClientError(f"invalid JSON from RPC: {exc}") from exc

        if isinstance(data, dict) and data.get("error"):
            error = data["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise StellarClientError(f"RPC error: {message}")
        return (data or {}).get("result")

    def get_health(self) -> dict | None:
        return self._call("getHealth")

    def get_network(self) -> dict | None:
        return self._call("getNetwork")

    def latest_ledger(self) -> dict | None:
        return self._call("getLatestLedger")

    def get_latest_ledger(self) -> dict | None:
        """Alias for :meth:`latest_ledger` (matches the RPC method name)."""

        return self.latest_ledger()

    def get_events(
        self,
        start_ledger: int,
        contract_ids: list[str] | str | None = None,
        limit: int = 100,
        xdr_format: str | None = "base64",
    ) -> dict | None:
        """Fetch contract events starting at ``start_ledger``.

        ``getEvents`` uses a filter list; when no contract ids are supplied the
        filter still requests contract events (all contracts).
        """

        if isinstance(start_ledger, bool) or not isinstance(start_ledger, int):
            raise ValueError("start_ledger must be an integer")
        if start_ledger < 1:
            raise ValueError("start_ledger must be at least 1")
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ValueError("limit must be an integer")
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")

        if contract_ids is None:
            ids: list[str] = []
        elif isinstance(contract_ids, str):
            ids = [contract_ids]
        else:
            ids = list(contract_ids)

        contract_filter: dict = {"type": "contract"}
        if ids:
            contract_filter["contractIds"] = ids

        params: dict = {
            "startLedger": start_ledger,
            "filters": [contract_filter],
            "limit": limit,
        }
        if xdr_format:
            params["xdrFormat"] = xdr_format
        return self._call("getEvents", params)
