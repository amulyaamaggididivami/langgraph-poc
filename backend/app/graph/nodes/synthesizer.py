"""TASK-ORCHESTRATION-007: Synthesizer node.

comp-synthesizer (trd.md §Architecture Overview) — the mandatory final
aggregation step (BRD decision-03), never skippable: it always runs
after the Query Tool / Calculation Agent, regardless of which of them
ran. It combines the question, raw rows, and calculations into one
natural-language response, and must never leak schema/table names
(requirement-08, system.md SY-006).
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.llm import get_llm
from app.graph.state import OrchestratorState
from app.graph.timeout import with_timeout
from app.prompts.synthesizer import SYSTEM_PROMPT


def _default_llm() -> BaseChatModel:
    return get_llm()


def _build_user_message(state: OrchestratorState) -> str:
    parts = [f"Question: {state['question']}"]
    if state.get("raw_rows") is not None:
        parts.append(f"Raw rows: {state['raw_rows']}")
    if state.get("calculations") is not None:
        parts.append(f"Calculations: {state['calculations']}")
    return "\n\n".join(parts)


def synthesizer_node(state: OrchestratorState, llm: Optional[BaseChatModel] = None) -> dict:
    """LangGraph node: reads `state["question"]`, `state["raw_rows"]`, and
    `state["calculations"]`; returns a partial state update setting
    `synthesized_response` to one natural-language answer."""
    llm = llm or _default_llm()

    # TASK-ORCHESTRATION-018: bounded to decision-24's 30s iface-llm-provider deadline.
    response = with_timeout(
        llm.invoke,
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=_build_user_message(state)),
        ],
    )

    return {"synthesized_response": response.content}
