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

    def latest_ledger(self) -> dict | None:
        return self._call("getLatestLedger")
