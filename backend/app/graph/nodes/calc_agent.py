"""TASK-ORCHESTRATION-006: Calculation Agent node.

comp-calc-agent (trd.md §Technology Choices) — a deepagents.create_deep_agent()
graph with real aggregation tool functions, registered directly as a node
in the parent StateGraph (decision-29) — not wrapped in a manual
`.invoke()` call, so its internal tool-calling loop shares the parent's
PostgresSaver and each tool call gets its own checkpoint entry.

Tool functions themselves live in app/tools/calculator/ (one per file);
see that package's docstring for the two BRD-named aggregation types
that don't have a tool here yet.
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from deepagents import create_deep_agent

from app.graph.llm import get_llm
from app.prompts.calc_agent import SYSTEM_PROMPT
from app.tools.calculator import TOOLS


def build_calc_agent(llm: Optional[BaseChatModel] = None) -> CompiledStateGraph:
    """Builds the Calculation Agent subgraph. Deliberately no checkpointer
    argument here — per decision-29, this must be compiled with none of
    its own so it inherits whichever PostgresSaver the parent graph
    (TASK-ORCHESTRATION-008) is compiled with when this is registered
    directly as a node."""
    llm = llm or get_llm()
    return create_deep_agent(model=llm, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
