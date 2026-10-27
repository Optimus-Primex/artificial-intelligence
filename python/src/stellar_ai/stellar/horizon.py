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

    def recent_ledgers(self, limit: int = 20) -> list[dict]:
        """Return up to ``limit`` of the most recently closed ledgers."""

        try:
            parsed_limit = int(limit)
        except (TypeError, ValueError):
            parsed_limit = 20
        parsed_limit = max(1, min(parsed_limit, 200))
        data = self._get("/ledgers", {"order": "desc", "limit": parsed_limit})
        records = (data or {}).get("_embedded", {}).get("records", [])
        return [record for record in records if isinstance(record, dict)]

    def latest_ledger(self) -> dict | None:
        """Return the most recently closed ledger record, if any."""

        records = self.recent_ledgers(1)
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
