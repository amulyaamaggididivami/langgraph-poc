"""TASK-ORCHESTRATION-008: Wire the StateGraph (Orchestrator).

comp-orchestrator (trd.md §Architecture Overview) — not a node itself,
this *is* the StateGraph: the edges and conditional routing connecting
Planner, Query Tool, Calculation Agent, and Synthesizer, enforcing
dependency order (BRD FR-005/FR-008/FR-009). Planner decides
Plan-or-Decline; a declined question ends immediately. Otherwise,
which of Query Tool / Calculation Agent runs first is decided by each
Task's own `depends_on` (`_next_runnable_task`), not a fixed node
order: a Plan can be query-then-calculate (the common case), query-only
(no calculation needed), or calculation-only with no query task at all
(e.g. "what is 2+3" — the numbers are already in the question, nothing
to fetch). Synthesizer always runs last regardless of which of the
other two ran, per BRD decision-03.

The Calculation Agent's node function (`make_calc_agent_node`) lives in
`app/graph/nodes/calc_agent.py` alongside `build_calc_agent()` — see
that module's docstring for why it's a translation wrapper rather than
direct registration (its state schema shares no field names with
`OrchestratorState`). That reasoning does NOT extend to this graph's own
boundary with TASK-ORCHESTRATION-009's chat route: `OrchestratorState`
is this project's own schema, not a third-party library's fixed
contract, so there is no reason it can't carry `messages` directly.
`extract_question`/`finalize` below are that boundary, as two ordinary
nodes on this same graph — not a second StateGraph wrapping this one.

TASK-ORCHESTRATION-014 will insert a human-approval node between
`synthesizer` and `finalize`; this graph goes straight through for now.
"""

from typing import Optional

from langchain_core.messages import AIMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.nodes.calc_agent import build_calc_agent, make_calc_agent_node
from app.graph.nodes.planner import planner_node
from app.graph.nodes.query_tool import query_execution_tool_node
from app.graph.nodes.synthesizer import synthesizer_node
from app.graph.state import OrchestratorState


def extract_question_node(state: OrchestratorState) -> dict:
    """Lets this graph be driven either directly (tests, scripts — pass
    `question` in the initial state) or via chat (ag-ui-langgraph only
    ever supplies `messages`). If `question` is already set, this is a
    no-op."""
    if state.get("question"):
        return {}
    messages = state.get("messages")
    if messages:
        return {"question": messages[-1].content}
    raise ValueError("build_graph() needs either state['question'] or state['messages']")


def finalize_node(state: OrchestratorState) -> dict:
    """Appends one reply message summarizing however this run ended —
    declined or synthesized — so a chat-driven caller has something to
    show, without every other node needing to know `messages` exists."""
    if state.get("decline_reason") is not None:
        reply = f"I can't help with that ({state['decline_reason']})."
    else:
        reply = state.get("synthesized_response") or "No response was produced."
    return {"messages": [AIMessage(content=reply)]}


def _next_runnable_task(tasks: list[dict]) -> Optional[dict]:
    """The first PENDING task whose declared `depends_on` are all already
    COMPLETED — this is what BRD FR-005/FR-008/FR-009's dependency-ordered
    execution actually means: which task runs next comes from the Plan's
    own dependency graph, not from a fixed query-then-calculate order. A
    Plan with only a `calculation_agent` task and no `query_execution_tool`
    task at all is valid (e.g. "what is 2+3") and has no unmet dependency,
    so it's runnable immediately."""
    completed_ids = {t["id"] for t in tasks if t["status"] == "COMPLETED"}
    for task in tasks:
        if task["status"] == "PENDING" and all(dep in completed_ids for dep in task["depends_on"]):
            return task
    return None


def _route_after_planner(state: OrchestratorState) -> str:
    if state.get("decline_reason") is not None:
        return "declined"
    task = _next_runnable_task(state["plan"]["tasks"])
    if task is None:
        raise ValueError("planner produced a plan with no runnable task")
    return "query_tool" if task["executor"] == "query_execution_tool" else "calc_agent"


def _route_after_query_tool(state: OrchestratorState) -> str:
    task = _next_runnable_task(state["plan"]["tasks"])
    return "calc_agent" if task is not None and task["executor"] == "calculation_agent" else "synthesizer"


def build_graph(
    *,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    planner=None,
    query_tool=None,
    calc_agent=None,
    synthesizer=None,
) -> CompiledStateGraph:
    """Assembles and compiles the Orchestrator. Every node defaults to the
    real implementation; each can be overridden (tests pass fakes to
    avoid real LLM/tool calls). `calc_agent`, if given, must be a compiled
    graph exposing `.invoke(input, config)` like `build_calc_agent()`'s
    return value."""
    planner = planner or planner_node
    query_tool = query_tool or query_execution_tool_node
    calc_agent = calc_agent or build_calc_agent()
    synthesizer = synthesizer or synthesizer_node

    graph = StateGraph(OrchestratorState)
    graph.add_node("extract_question", extract_question_node)
    graph.add_node("planner", planner)
    graph.add_node("query_tool", query_tool)
    graph.add_node("calc_agent", make_calc_agent_node(calc_agent))
    graph.add_node("synthesizer", synthesizer)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "extract_question")
    graph.add_edge("extract_question", "planner")
    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {"declined": "finalize", "query_tool": "query_tool", "calc_agent": "calc_agent"},
    )
    graph.add_conditional_edges(
        "query_tool", _route_after_query_tool, {"calc_agent": "calc_agent", "synthesizer": "synthesizer"}
    )
    graph.add_edge("calc_agent", "synthesizer")
    graph.add_edge("synthesizer", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=checkpointer)
