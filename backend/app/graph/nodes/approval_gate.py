"""TASK-ORCHESTRATION-014: Human Approval gate.

Implements the `AwaitingReview` pause from trd.md §State Machines. Only
sits on the path where the Synthesizer actually produced a response —
a declined question goes straight to a terminal state and never reaches
this node (trd.md's state table has no `Declined -> AwaitingReview`
transition).

Uses LangGraph's own `interrupt()`: calling it inside a node halts that
node's execution before it returns anything, so this node has not yet
completed when the pause happens. `constraint-checkpoint-freshness`
("the checkpoint write happens in the same graph step that produces
the Response, before the node returns") is satisfied by construction,
not by anything this node does — the Synthesizer's own step already
wrote a checkpoint containing `synthesized_response` one step earlier,
before the graph ever reached here. If the process crashes right after
the interrupt fires, `get_state()` on restart shows `next=('approval_gate',)`
with the Response already present — resuming re-runs only this node,
never the Synthesizer/Query Tool/Calculation Agent again.

Writes `requests.state = 'AwaitingReview'` (trd.md's own side effect for
this transition) before calling `interrupt()` — originally missed when
this node was first built; a request reached the pause correctly but
the project-owned tracking table never reflected it, so
TASK-ORCHESTRATION-016's pending-list query had nothing real to return.
Note this write re-runs (harmlessly — it's the same value) every time
this node is re-entered on resume, since LangGraph re-executes a node's
full body from the top when resuming past an `interrupt()` call; the
row is overwritten to `Delivered`/`Withheld` immediately after by
whatever resumed it.

Resuming happens via `graph.ainvoke(Command(resume={"decision": "approve"
| "reject"}), config)` — TASK-ORCHESTRATION-015's `/review` route is
what actually calls that from the outside.
"""

from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from app.graph.state import OrchestratorState
from app.persistence import requests_repo as default_requests_repo


def make_approval_gate_node(repo=default_requests_repo):
    async def approval_gate_node(state: OrchestratorState, config: RunnableConfig) -> dict:
        thread_id = config["configurable"]["thread_id"]
        await repo.update_state(thread_id, "AwaitingReview")

        decision = interrupt(
            {
                "question": state.get("question"),
                "synthesized_response": state.get("synthesized_response"),
            }
        )
        approved = decision.get("decision") == "approve"
        return {"human_approval": "approved" if approved else "rejected"}

    return approval_gate_node
