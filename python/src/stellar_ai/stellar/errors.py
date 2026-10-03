"""Errors raised by Stellar/Soroban clients."""

from __future__ import annotations


class StellarClientError(RuntimeError):
    """Raised when a Stellar/Soroban endpoint is unreachable or returns bad data."""
