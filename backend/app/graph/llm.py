"""Shared LLM factory for every graph node that calls out to an LLM.

trd.md decision-28 specifies Google Gemini via `langchain_google_genai`
directly against Google's API. Superseded per the PTL's instruction
(2026-09-08): route through a LiteLLM proxy instead, using
`langchain_openai.ChatOpenAI` (OpenAI-compatible wire format, same
underlying Gemini model) — a code-level swap only. trd.md's decision-28
text still names langchain-google-genai; needs a TRD amendment before
this is fully contract-clean, flagging rather than silently editing an
approved, hash-tracked TRD section.
"""

import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

_DEFAULT_MODEL = "gemini-3.6-flash"


def get_llm(*, model_env_var: str, temperature: float = 0) -> BaseChatModel:
    """Builds a LiteLLM-proxied chat model. `model_env_var` lets each node
    override the model independently (e.g. `PLANNER_MODEL`) while sharing
    one proxy endpoint; falls back to `_DEFAULT_MODEL` if unset.

    Raises `KeyError` with a clear message if the proxy isn't configured —
    fails loud, not with a silent fallback to some other provider.
    """
    model = os.environ.get(model_env_var, _DEFAULT_MODEL)
    try:
        api_key = os.environ["LITELLM_API_KEY"]
        base_url = os.environ["LITELLM_BASE_URL"]
    except KeyError as e:
        raise KeyError(
            f"{e.args[0]} not set — required to reach the LiteLLM proxy "
            "(see backend/.env.example)"
        ) from e
    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=temperature)
