"""Shared LangGraph state schema for the ORCHESTRATION module.

Mirrors the JSON shape frozen in trd.md's Data Model section. `plan`,
`synthesized_response`, and `decline_reason` live inside this one
TypedDict — checkpointed by PostgresSaver as an opaque blob, not a
separate SQL table (decision-26). Node functions read/write it as a
partial dict, so every field is optional here.

`messages` is the one field trd.md doesn't name — it exists so this
same graph can be driven directly by ag-ui-langgraph's chat-history
protocol (TASK-ORCHESTRATION-009), not just by a bare `question` string.
Unlike comp-calc-agent's `messages`/`todos`/`files` shape, this one is
ours to define either way, so there's no translation-wrapper graph
sitting on top of this one — graph.py's own extract_question/finalize
nodes read and write it directly.
"""

from typing import Annotated

# typing.TypedDict fails ag-ui-langgraph's schema introspection on
# Python <3.12 (pydantic's TypeAdapter rejects it) — confirmed by the
# TASK-ORCHESTRATION-001 spike. Every graph state type must import from
# typing_extensions instead.
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class OrchestratorState(TypedDict, total=False):
    question: str
    plan: dict | None
    raw_rows: list | None
    calculations: dict | None
    synthesized_response: str | None
    decline_reason: str | None
    human_approval: str | None
    messages: Annotated[list, add_messages]
