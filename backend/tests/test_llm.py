"""Unit tests for the shared LiteLLM-proxied model factory."""

import pytest

from app.graph.llm import get_llm


def test_get_llm_fails_loud_without_proxy_config(monkeypatch):
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.delenv("LITELLM_BASE_URL", raising=False)

    with pytest.raises(KeyError, match="LITELLM_API_KEY"):
        get_llm(model_env_var="PLANNER_MODEL")


def test_get_llm_builds_chat_openai_against_the_proxy(monkeypatch):
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_BASE_URL", "https://litellm.example.com")
    monkeypatch.setenv("PLANNER_MODEL", "gemini-3.6-flash")

    llm = get_llm(model_env_var="PLANNER_MODEL")

    assert llm.model_name == "gemini-3.6-flash"
    assert str(llm.openai_api_base) == "https://litellm.example.com"


def test_get_llm_falls_back_to_default_model(monkeypatch):
    monkeypatch.setenv("LITELLM_API_KEY", "test-key")
    monkeypatch.setenv("LITELLM_BASE_URL", "https://litellm.example.com")
    monkeypatch.delenv("PLANNER_MODEL", raising=False)

    llm = get_llm(model_env_var="PLANNER_MODEL")

    assert llm.model_name == "gemini-3.6-flash"
