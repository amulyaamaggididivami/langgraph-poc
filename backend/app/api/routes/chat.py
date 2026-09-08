"""TASK-ORCHESTRATION-009: Chat Route (/chat).

comp-chat-route (trd.md §API Contracts, iface-chat-api v1.0.0) — SSE
endpoint via ag-ui-langgraph's add_langgraph_fastapi_endpoint
(decision-25), wired directly to the real compiled Orchestrator graph
(TASK-ORCHESTRATION-008's build_graph()). No wrapper graph here —
`OrchestratorState` carries `messages` itself (see app/graph/state.py
and graph.py's extract_question/finalize nodes), so this route just
hands the Orchestrator graph straight to ag-ui-langgraph.

Flagged deviation from trd.md, not silently worked around (per the
TASK-ORCHESTRATION-001 spike's own decision budget — this is exactly
the "SSE event shape doesn't match what trd.md assumed" case, escalated
and decided 2026-09-08 rather than picked unilaterally): trd.md
documents /chat's request body as `{thread_id, question}`. What
add_langgraph_fastapi_endpoint's route actually requires is
ag-ui-protocol's own `RunAgentInput` — `threadId`, `runId`, `messages`
(a list), `tools`, `context`, `forwardedProps`; there is no bare
`question` field. Decision: keep add_langgraph_fastapi_endpoint
unwrapped and treat `question` as the last message's content — trd.md
needs an amendment to match, not done here (an approved, hash-tracked
doc). TASK-ORCHESTRATION-009's own acceptance criterion "request body
validates against trd.md's JSON Schema" cannot be literally true given
this decision; documenting that plainly rather than papering over it.

No human-approval gate exists yet (TASK-ORCHESTRATION-014) — this route
streams straight from Synthesizer to the client. That's an accurate
reflection of where the graph actually ends today, not a shortcut.
"""

from typing import Optional

from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint
from fastapi import FastAPI
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.graph.graph import build_graph


def register_chat_route(app: FastAPI, *, checkpointer: Optional[BaseCheckpointSaver] = None) -> None:
    """Registers POST /chat (+ GET /chat/health) on `app`."""
    compiled = build_graph(checkpointer=checkpointer)
    agent = LangGraphAgent(name="orchestrator", graph=compiled)
    add_langgraph_fastapi_endpoint(app, agent, path="/chat")
