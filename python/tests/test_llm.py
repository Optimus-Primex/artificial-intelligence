"""LLM provider tests."""

from __future__ import annotations

import pytest

from stellar_ai.llm import StaticProvider, build_provider


def test_build_static_provider():
    provider = build_provider("static")
    assert isinstance(provider, StaticProvider)
    assert provider.name == "static"


def test_build_provider_is_case_insensitive():
    assert build_provider("STATIC").name == "static"


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        build_provider("does-not-exist")


def test_static_provider_is_deterministic():
    provider = StaticProvider()
    first = provider.complete("hello   world")
    second = provider.complete("hello   world")
    assert first == second
    assert "hello world" in first
