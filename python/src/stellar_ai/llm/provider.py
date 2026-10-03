"""Model provider interface plus a deterministic default.

Real providers (OpenAI, Anthropic, a local Ollama server, ...) implement
:class:`LLMProvider` and register in :data:`_PROVIDERS`. The default
``StaticProvider`` never makes a network call, so the entire service runs and
tests without credentials.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal contract every provider implements."""

    name: str

    def complete(self, prompt: str) -> str:
        """Return a completion for ``prompt``."""


class StaticProvider:
    """Deterministic provider used for development, CI and tests."""

    name = "static"

    def complete(self, prompt: str) -> str:
        context = " ".join(prompt.split())[:400]
        return f"Deterministic stub response (no model configured). Grounded context: {context}"


_PROVIDERS: dict[str, type] = {
    "static": StaticProvider,
}


def build_provider(name: str) -> LLMProvider:
    """Instantiate a registered provider by name."""

    try:
        factory = _PROVIDERS[name.strip().lower()]
    except KeyError:
        allowed = ", ".join(sorted(_PROVIDERS))
        raise ValueError(f"unknown llm provider: {name!r} (expected one of: {allowed})") from None
    return factory()
