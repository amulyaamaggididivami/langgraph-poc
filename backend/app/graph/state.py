"""Shared LangGraph state schema for the ORCHESTRATION module.

Mirrors the JSON shape frozen in trd.md's Data Model section. `plan`,
`synthesized_response`, and `decline_reason` live inside this one
TypedDict — checkpointed by PostgresSaver as an opaque blob, not a
separate SQL table (decision-26). Node functions read/write it as a
partial dict, so every field is optional here.
"""

# typing.TypedDict fails ag-ui-langgraph's schema introspection on
# Python <3.12 (pydantic's TypeAdapter rejects it) — confirmed by the
# TASK-ORCHESTRATION-001 spike. Every graph state type must import from
# typing_extensions instead.
from typing_extensions import TypedDict


class OrchestratorState(TypedDict, total=False):
    question: str
    plan: dict | None
    raw_rows: list | None
    calculations: dict | None
    synthesized_response: str | None
    decline_reason: str | None
    human_approval: str | None
