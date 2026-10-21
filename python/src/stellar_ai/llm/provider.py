"""Model provider interface, a real HTTP provider, and a deterministic default.

The service ships with two providers:

* ``static`` — a deterministic, network-free stub used in development and tests.
* ``openai`` — any OpenAI-compatible ``/chat/completions`` endpoint (OpenAI,
  local vLLM/Ollama gateways, ...), configured with ``STELLAR_AI_LLM_*``.

Additional providers implement :class:`LLMProvider` and can be added to
:func:`build_provider`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import httpx


class LLMError(RuntimeError):
    """Raised when a provider is misconfigured or the upstream call fails."""


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


class OpenAICompatibleProvider:
    """Chat-completions provider for OpenAI-compatible HTTP APIs."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        http_post=None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http_post = http_post

    def complete(self, prompt: str) -> str:
        if not self.api_key:
            raise LLMError(
                "openai provider requires STELLAR_AI_LLM_API_KEY "
                "(use STELLAR_AI_LLM_PROVIDER=static for offline development)"
            )

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"

        try:
            if self._http_post is not None:
                data = self._http_post(url, payload, headers, self.timeout)
            else:
                response = httpx.post(url, json=payload, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise LLMError(f"model request failed: {exc}") from exc
        except ValueError as exc:
            raise LLMError(f"model returned invalid JSON: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("model response did not contain a completion") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMError("model returned an empty completion")
        return content.strip()


def build_provider(
    name: str,
    *,
    api_key: str = "",
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
    timeout: float = 30.0,
) -> LLMProvider:
    """Instantiate a provider by name.

    ``openai`` and ``openai-compatible`` are aliases for the same HTTP
    provider; point ``base_url`` at a local gateway to use a local model.
    """

    key = name.strip().lower()
    if key == "static":
        return StaticProvider()
    if key in {"openai", "openai-compatible"}:
        return OpenAICompatibleProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout,
        )
    allowed = "openai, openai-compatible, static"
    raise ValueError(f"unknown llm provider: {name!r} (expected one of: {allowed})")
