"""Minimal Stellar Horizon REST client.

The HTTP call is injectable via ``http_get`` so tests (and the agent) can run
without network access.
"""

from __future__ import annotations

import httpx

from .errors import StellarClientError


class HorizonClient:
    def __init__(self, base_url: str, timeout: float = 10.0, http_get=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http_get = http_get

    def _get(self, path: str, params: dict | None = None):
        url = f"{self.base_url}{path}"
        if self._http_get is not None:
            return self._http_get(url, params)
        try:
            response = httpx.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise StellarClientError(str(exc)) from exc
        except ValueError as exc:
            raise StellarClientError(f"invalid JSON from Horizon: {exc}") from exc

    def latest_ledger(self) -> dict | None:
        """Return the most recently closed ledger record, if any."""

        data = self._get("/ledgers", {"order": "desc", "limit": 1})
        records = (data or {}).get("_embedded", {}).get("records", [])
        return records[0] if records else None

    def account(self, account_id: str) -> dict:
        """Return a Horizon account record."""

        return self._get(f"/accounts/{account_id}") or {}

    def recent_payments(self, limit: int = 50) -> list[dict]:
        """Return the most recent payment-like operations, newest first.

        Horizon's ``/payments`` endpoint does not reliably filter by asset, so
        callers receive the raw window and filter it with the analyzers.
        """

        data = self._get(
            "/payments",
            {"order": "desc", "limit": limit, "include_failed": "false"},
        )
        records = (data or {}).get("_embedded", {}).get("records", [])
        return records if isinstance(records, list) else []
