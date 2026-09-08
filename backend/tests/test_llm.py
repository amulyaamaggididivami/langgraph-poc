"""Unit tests for the shared LiteLLM-proxied model factory.

All three agents share one model (PTL instruction, 2026-09-08) — there
is no per-node model override, so `get_llm()` takes no model argument
and always reads `LITELLM_PROVIDER_MODEL_NAME`.
"""

import pytest

from app.graph.llm import get_llm


def test_get_llm_fails_loud_without_api_key(monkeypatch):
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.setenv("LITELLM_PROVIDER_BASE_URL", "https://litellm.example.com")
    monkeypatch.setenv("LITELLM_PROVIDER_MODEL_NAME", "gemini-3.6-flash")

    with pytest.raises(KeyError, match="LITELLM_API_KEY"):
        get_llm()


def test_get_llm_fails_loud_without_base_url(monkeypatch):
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.delenv("LITELLM_PROVIDER_BASE_URL", raising=False)
    monkeypatch.setenv("LITELLM_PROVIDER_MODEL_NAME", "gemini-3.6-flash")

    with pytest.raises(KeyError, match="LITELLM_PROVIDER_BASE_URL"):
        get_llm()


def test_get_llm_fails_loud_without_model_name(monkeypatch):
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_PROVIDER_BASE_URL", "https://litellm.example.com")
    monkeypatch.delenv("LITELLM_PROVIDER_MODEL_NAME", raising=False)

    with pytest.raises(KeyError, match="LITELLM_PROVIDER_MODEL_NAME"):
        get_llm()


def test_get_llm_builds_chat_openai_against_the_proxy(monkeypatch):
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_PROVIDER_BASE_URL", "https://litellm.example.com")
    monkeypatch.setenv("LITELLM_PROVIDER_MODEL_NAME", "gemini-3.6-flash")

    llm = get_llm()

    assert llm.model_name == "gemini-3.6-flash"
    assert str(llm.openai_api_base) == "https://litellm.example.com"
