"""TASK-ORCHESTRATION-006: Calculation Agent node.

comp-calc-agent (trd.md §Technology Choices) — a deepagents.create_deep_agent()
graph with real aggregation tool functions, registered directly as a node
in the parent StateGraph (decision-29) — not wrapped in a manual
`.invoke()` call, so its internal tool-calling loop shares the parent's
PostgresSaver and each tool call gets its own checkpoint entry.

Tool set: BRD §Scope names sum, average, min/max, count, percentage,
ratio, "group-based aggregation", and "derived metrics" as in-scope
aggregation types. The last two aren't single well-shaped functions —
"group-based aggregation" implies a grouping key the Query Tool's
predefined queries would need to supply, and "derived metrics" is
undefined beyond that label. Both need PTL clarification before they
get a tool signature; everything else below is unambiguous and built.
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from deepagents import create_deep_agent

from app.graph.llm import get_llm

SYSTEM_PROMPT = """You are the Calculation Agent for a data-analysis \
assistant. You receive a calculation task description and a set of raw \
numeric rows already fetched by another step — you never fetch rows \
yourself. Pick the tool(s) that answer the task, chaining multiple \
calls when the task requires it (e.g. a ratio or percentage change \
needs two prior aggregates first). Return the final numeric result and \
a one-line explanation of how you got it."""


def sum_values(numbers: list[float]) -> float:
    """Add up a list of numbers."""
    return sum(numbers)


def average(numbers: list[float]) -> float:
    """Arithmetic mean of a list of numbers."""
    return sum(numbers) / len(numbers)


def minimum(numbers: list[float]) -> float:
    """Smallest value in a list of numbers."""
    return min(numbers)


def maximum(numbers: list[float]) -> float:
    """Largest value in a list of numbers."""
    return max(numbers)


def count_values(items: list) -> int:
    """Count of items in a list. Unlike the other tools, this one doesn't
    require numbers — "how many appointments/rows/orders" needs to count
    raw_rows (a list of record dicts from the Query Tool), not a list of
    already-extracted numeric values."""
    return len(items)


def percentage(part: float, whole: float) -> float:
    """What percentage `part` is of `whole`."""
    return (part / whole) * 100


def percentage_change(old: float, new: float) -> float:
    """Percentage change from `old` to `new` (negative if it decreased)."""
    return ((new - old) / old) * 100


def ratio(a: float, b: float) -> float:
    """Ratio of `a` to `b`."""
    return a / b


TOOLS = [sum_values, average, minimum, maximum, count_values, percentage, percentage_change, ratio]


def build_calc_agent(llm: Optional[BaseChatModel] = None) -> CompiledStateGraph:
    """Builds the Calculation Agent subgraph. Deliberately no checkpointer
    argument here — per decision-29, this must be compiled with none of
    its own so it inherits whichever PostgresSaver the parent graph
    (TASK-ORCHESTRATION-008) is compiled with when this is registered
    directly as a node."""
    llm = llm or get_llm()
    return create_deep_agent(model=llm, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
