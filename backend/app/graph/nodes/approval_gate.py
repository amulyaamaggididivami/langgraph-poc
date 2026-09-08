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

Resuming happens via `graph.invoke(Command(resume={"decision": "approve"
| "reject"}), config)` — TASK-ORCHESTRATION-015's `/review` route is
what actually calls that from the outside.
"""

from langgraph.types import interrupt

from app.graph.state import OrchestratorState


def approval_gate_node(state: OrchestratorState) -> dict:
    decision = interrupt(
        {
            "question": state.get("question"),
            "synthesized_response": state.get("synthesized_response"),
        }
    )
    approved = decision.get("decision") == "approve"
    return {"human_approval": "approved" if approved else "rejected"}
