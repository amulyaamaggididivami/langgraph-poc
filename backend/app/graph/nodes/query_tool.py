"""TASK-ORCHESTRATION-004: Query Execution Tool node.

comp-query-tool (trd.md §Architecture Overview) — deterministic, no
LLM. Dispatches one of BRD constraint-02's fixed predefined queries and
returns raw rows. Read-only by construction: this module contains no
write statement, so constraint-01 holds regardless of which query runs.

iface-business-db's real schema is TASK-ORCHESTRATION-022/023 (Engineer
A, not yet built) — until then this dispatches against the fixture
registry in app/constants/query_tool.py, matched by keyword against the
assigned Task's description.
"""

from typing import Callable, Optional

from app.constants.query_tool import DEFAULT_QUERY_KEY, PREDEFINED_QUERIES
from app.graph.state import OrchestratorState

QueryRunner = Callable[[str], list]


def _match_query_key(description: str) -> str:
    text = description.lower()
    for key, entry in PREDEFINED_QUERIES.items():
        if any(keyword in text for keyword in entry["keywords"]):
            return key
    return DEFAULT_QUERY_KEY


def _default_runner(query_key: str) -> list:
    return PREDEFINED_QUERIES[query_key]["rows"]


def _find_pending_task(tasks: list[dict]) -> Optional[dict]:
    for task in tasks:
        if task["executor"] == "query_execution_tool" and task["status"] == "PENDING":
            return task
    return None


def query_execution_tool_node(state: OrchestratorState, run_query: Optional[QueryRunner] = None) -> dict:
    """LangGraph node: finds the first PENDING `query_execution_tool` Task
    in `state["plan"]`, runs its matched predefined query, marks that
    Task COMPLETED, and returns the updated plan plus the raw rows."""
    run_query = run_query or _default_runner

    plan = state["plan"]
    tasks = [dict(t) for t in plan["tasks"]]
    task = _find_pending_task(tasks)
    if task is None:
        raise ValueError(
            "query_execution_tool_node called with no PENDING query_execution_tool Task in the plan"
        )

    query_key = _match_query_key(task["description"])
    rows = run_query(query_key)
    task["status"] = "COMPLETED"

    return {"plan": {**plan, "tasks": tasks}, "raw_rows": rows}
