"""Tests for the OpenAI-compatible provider (no network)."""

from __future__ import annotations

import httpx
import pytest

from stellar_ai.llm import LLMError, OpenAICompatibleProvider, build_provider


def _provider(http_post=None) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        api_key="test-key",
        model="test-model",
        base_url="https://models.example/v1/",
        http_post=http_post,
    )


def test_complete_sends_chat_completions_request():
    captured = {}

    def http_post(url, payload, headers, timeout):
        captured.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return {"choices": [{"message": {"content": "  the network is healthy  "}}]}

    answer = _provider(http_post).complete("status?")

    assert answer == "the network is healthy"
    assert captured["url"] == "https://models.example/v1/chat/completions"
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["messages"] == [{"role": "user", "content": "status?"}]
    assert captured["headers"]["Authorization"] == "Bearer test-key"


def test_missing_api_key_is_a_clear_error():
    provider = OpenAICompatibleProvider(api_key="")
    with pytest.raises(LLMError, match="STELLAR_AI_LLM_API_KEY"):
        provider.complete("hello")


def test_http_failure_becomes_llm_error(monkeypatch):
    def fake_post(*_args, **_kwargs):
        raise httpx.HTTPError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(LLMError, match="model request failed"):
        _provider().complete("hello")


def test_malformed_response_becomes_llm_error():
    provider = _provider(lambda *_args: {"choices": []})
    with pytest.raises(LLMError, match="did not contain a completion"):
        provider.complete("hello")


def test_empty_completion_is_rejected():
    provider = _provider(lambda *_args: {"choices": [{"message": {"content": "   "}}]})
    with pytest.raises(LLMError, match="empty completion"):
        provider.complete("hello")


def test_build_provider_accepts_openai_aliases():
    for name in ("openai", "openai-compatible", "OpenAI"):
        provider = build_provider(name, api_key="k")
        assert isinstance(provider, OpenAICompatibleProvider)
        assert provider.name == "openai"
