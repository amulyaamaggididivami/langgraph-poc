"""TASK-ORCHESTRATION-008: Wire the StateGraph (Orchestrator).

comp-orchestrator (trd.md §Architecture Overview) — not a node itself,
this *is* the StateGraph: the edges and conditional routing connecting
Planner, Query Tool, Calculation Agent, and Synthesizer, enforcing
dependency order (BRD FR-005/FR-008/FR-009). A decline can happen in
two places, not just one (2026-09-08 PTL direction): the Planner
declines a question that isn't plausibly about this business's data at
all, ending immediately; the Query Tool can *also* decline, after a
Plan already exists, if the assigned Task's description matches none of
the predefined queries it actually has (`_route_after_query_tool`) —
the Planner is deliberately permissive about domain fit, so this second
gate is where "plausible but not actually backed by a real query" gets
caught. Otherwise, which of Query Tool / Calculation Agent runs first is
decided by each Task's own `depends_on` (`_next_runnable_task`), not a
fixed node order: a Plan can be query-then-calculate (the common case),
query-only (no calculation needed), or calculation-only with no query
task at all (e.g. "what is 2+3" — the numbers are already in the
question, nothing to fetch). Synthesizer always runs last regardless of
which of the other two ran, per BRD decision-03.

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

TASK-ORCHESTRATION-014's `approval_gate` sits between `synthesizer` and
`finalize`: it pauses the run (via `interrupt()`) until an external
caller resumes with an approve/reject decision — see
`app/graph/nodes/approval_gate.py`. Only the synthesized-response path
goes through it; a declined question routes through `record_decline`
instead, matching trd.md's state table (no `Declined -> AwaitingReview`
edge).

`extract_question`/`record_decline`/`approval_gate` are also where the
`requests` table (trd.md §Data Model) gets written — trd.md's state
table assigns `Received`/`BeingAnalyzed` to "POST /chat"/"Planner
begins" and `Declined` to "Planner's intent-match fails", but nothing
actually wrote them until this fix (found by testing: a real run
reached `AwaitingReview` correctly, yet the `requests` table stayed
completely empty — TASK-ORCHESTRATION-016's pending-list query had
nothing real to return). Doing it here, not inside `planner.py` itself,
keeps that node's own job (the LLM call) free of persistence concerns —
`extract_question` already runs immediately before the Planner with no
branching in between, so folding the `Received`→`BeingAnalyzed` pair
into one node is a faithful, not a shortcut, reading of the state
table's own transitions.

`extract_question` also resets every per-cycle field (`plan`, `raw_rows`,
`calculations`, `synthesized_response`, `decline_reason`,
`human_approval`) and always re-derives `question` from the latest
human message when chat-driven — found necessary by testing a real
multi-turn conversation: a `thread_id` is one whole chat conversation,
not one question. `messages` is genuine conversation history and stays
untouched across turns (the Planner reads it for context — see
planner.py); everything else here is per-turn scratch state. Without
this reset, LangGraph's own checkpointing (state persists across every
turn on the same thread, which is the point of checkpointing) meant
turn 2's Planner call ran correctly but the *routing* after it still
saw turn 1's leftover `decline_reason` and misrouted — a second, real
question silently reusing the first turn's answer. `extract_question`
is the right place for this because it's the one node LangGraph runs at
the start of every new cycle and never re-runs mid-resume (resuming an
`interrupt()` continues from wherever it paused, never back through
`extract_question`), so "this node just ran" reliably means "a genuinely
new question just arrived on this thread", not "we're continuing an
existing one".
"""

from typing import Optional

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph.nodes.approval_gate import make_approval_gate_node
from app.graph.nodes.calc_agent import build_calc_agent, make_calc_agent_node
from app.graph.nodes.planner import planner_node
from app.graph.nodes.query_tool import query_execution_tool_node
from app.graph.nodes.synthesizer import synthesizer_node
from app.graph.state import OrchestratorState
from app.persistence import requests_repo as default_requests_repo


def make_extract_question_node(repo=default_requests_repo):
    async def extract_question_node(state: OrchestratorState, config: RunnableConfig) -> dict:
        """Lets this graph be driven either directly (tests, scripts —
        pass `question` in the initial state) or via chat
        (ag-ui-langgraph only ever supplies `messages`). Also where
        `requests` gets its `Received` row and immediate `BeingAnalyzed`
        update — trd.md's own two transitions for "a question arrives
        and the Planner is about to look at it", collapsed into one
        node since nothing observable happens between them.

        Chat-driven runs always re-derive `question` from the latest
        human message rather than trusting a possibly-stale
        `state["question"]` left over from an earlier turn on this same
        thread — see module docstring. The direct/test invocation path
        (no `messages` at all) keeps using `state["question"]` verbatim,
        since there's no conversation to re-derive it from."""
        thread_id = config["configurable"]["thread_id"]
        messages = state.get("messages")

        if messages:
            question = None
            for message in reversed(messages):
                if getattr(message, "type", None) == "human":
                    question = message.content
                    break
            if question is None:
                raise ValueError("build_graph() got state['messages'] with no human message in it")
        elif state.get("question"):
            question = state["question"]
        else:
            raise ValueError("build_graph() needs either state['question'] or state['messages']")

        await repo.insert_received(thread_id, question)
        await repo.update_state(thread_id, "BeingAnalyzed")

        return {
            "question": question,
            "plan": None,
            "raw_rows": None,
            "calculations": None,
            "synthesized_response": None,
            "decline_reason": None,
            "human_approval": None,
        }

    return extract_question_node


def make_record_decline_node(repo=default_requests_repo):
    async def record_decline_node(state: OrchestratorState, config: RunnableConfig) -> dict:
        """`BeingAnalyzed -> Declined`: trd.md's side effect for the
        Planner's intent-match failing. A pass-through node purely for
        this write — routing already decided `decline_reason` is set."""
        thread_id = config["configurable"]["thread_id"]
        await repo.update_state(thread_id, "Declined", decline_reason=state["decline_reason"])
        return {}

    return record_decline_node


def finalize_node(state: OrchestratorState) -> dict:
    """Appends one reply message summarizing however this run ended —
    declined, rejected at review, or delivered — so a chat-driven caller
    has something to show, without every other node needing to know
    `messages` exists."""
    if state.get("decline_reason") is not None:
        reply = f"I can't help with that ({state['decline_reason']})."
    elif state.get("human_approval") == "rejected":
        reply = "This response was reviewed and withheld."
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
    tasks = state["plan"]["tasks"]
    if not tasks:
        # A greeting/pleasantry ("hi") is a Plan with zero Tasks, not a
        # decline — nothing to fetch or calculate, so it goes straight
        # to the Synthesizer, which generates a reply from the question
        # alone. Still goes through the same approval_gate/review path
        # as a real answer, per the PTL's direction: a greeting is
        # reviewed and delivered like anything else, not special-cased
        # around the human-approval step.
        return "synthesizer"
    task = _next_runnable_task(tasks)
    if task is None:
        raise ValueError("planner produced a plan with no runnable task")
    return "query_tool" if task["executor"] == "query_execution_tool" else "calc_agent"


def _route_after_query_tool(state: OrchestratorState) -> str:
    # The Query Tool can itself decline (no predefined query matched the
    # assigned Task) — same "declined" destination the Planner uses, a
    # decline discovered mid-execution rather than only up front.
    if state.get("decline_reason") is not None:
        return "declined"
    task = _next_runnable_task(state["plan"]["tasks"])
    return "calc_agent" if task is not None and task["executor"] == "calculation_agent" else "synthesizer"


def build_graph(
    *,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    planner=None,
    query_tool=None,
    calc_agent=None,
    synthesizer=None,
    requests_repo=None,
) -> CompiledStateGraph:
    """Assembles and compiles the Orchestrator. Every node defaults to the
    real implementation; each can be overridden (tests pass fakes to
    avoid real LLM/tool calls, or a real Postgres for the
    `requests`-table integration tests). `calc_agent`, if given, must be
    a compiled graph exposing `.invoke(input, config)` like
    `build_calc_agent()`'s return value. `requests_repo`, if given,
    replaces the module `extract_question`/`record_decline`/
    `approval_gate` otherwise write to directly."""
    planner = planner or planner_node
    query_tool = query_tool or query_execution_tool_node
    calc_agent = calc_agent or build_calc_agent()
    synthesizer = synthesizer or synthesizer_node
    repo = requests_repo or default_requests_repo

    graph = StateGraph(OrchestratorState)
    graph.add_node("extract_question", make_extract_question_node(repo))
    graph.add_node("planner", planner)
    graph.add_node("query_tool", query_tool)
    graph.add_node("calc_agent", make_calc_agent_node(calc_agent))
    graph.add_node("synthesizer", synthesizer)
    graph.add_node("record_decline", make_record_decline_node(repo))
    graph.add_node("approval_gate", make_approval_gate_node(repo))
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "extract_question")
    graph.add_edge("extract_question", "planner")
    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {
            "declined": "record_decline",
            "query_tool": "query_tool",
            "calc_agent": "calc_agent",
            "synthesizer": "synthesizer",
        },
    )
    graph.add_edge("record_decline", "finalize")
    graph.add_conditional_edges(
        "query_tool",
        _route_after_query_tool,
        {"declined": "record_decline", "calc_agent": "calc_agent", "synthesizer": "synthesizer"},
    )
    graph.add_edge("calc_agent", "synthesizer")
    graph.add_edge("synthesizer", "approval_gate")
    graph.add_edge("approval_gate", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=checkpointer)
