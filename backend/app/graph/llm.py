"""Shared LLM factory for every graph node that calls out to an LLM.

trd.md decision-28 specifies Google Gemini via `langchain_google_genai`
directly against Google's API. Superseded per the PTL's instruction
(2026-09-08): route through a LiteLLM proxy instead, using
`langchain_openai.ChatOpenAI` (OpenAI-compatible wire format, same
underlying Gemini model) — a code-level swap only. trd.md's decision-28
text still names langchain-google-genai; needs a TRD amendment before
this is fully contract-clean, flagging rather than silently editing an
approved, hash-tracked TRD section.

All three agents (Planner, Calculation Agent, Synthesizer) share one
model — there is no per-node override. `LITELLM_PROVIDER_MODEL_NAME` is
the single model name every node's LLM call uses (PTL instruction,
2026-09-08).
"""

import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI


def get_llm(*, temperature: float = 0) -> BaseChatModel:
    """Builds the one LiteLLM-proxied chat model shared by every node.

    Raises `KeyError` with a clear message if the proxy or model isn't
    configured — fails loud, not with a silent fallback to some other
    provider or model.
    """
    try:
        api_key = os.environ["LITELLM_API_KEY"]
        base_url = os.environ["LITELLM_PROVIDER_BASE_URL"]
        model = os.environ["LITELLM_PROVIDER_MODEL_NAME"]
    except KeyError as e:
        raise KeyError(
            f"{e.args[0]} not set — required to reach the LiteLLM proxy "
            "(see backend/.env.example)"
        ) from e
    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=temperature)
