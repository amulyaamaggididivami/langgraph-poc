"""Unit tests for TASK-ORCHESTRATION-004 (Query Execution Tool node).

Covers TEST-ORCHESTRATION-008. The "no write statement" half of that
Test ID's acceptance criteria is a static property of this module (it
contains no INSERT/UPDATE/DELETE and no business-DB write call) rather
than something to assert at runtime.
"""

import pytest

from app.constants.query_tool import PREDEFINED_QUERIES
from app.graph.nodes.query_tool import query_execution_tool_node


def _plan_with_query_task(description="total sales this month"):
    return {
        "tasks": [
            {
                "id": "t1",
                "description": description,
                "executor": "query_execution_tool",
                "depends_on": [],
                "status": "PENDING",
            }
        ]
    }


def test_returns_fixture_rows_for_matched_query():
    # TEST-ORCHESTRATION-008
    state = {"question": "what were total sales?", "plan": _plan_with_query_task("total sales last month")}

    update = query_execution_tool_node(state)

    assert update["raw_rows"] == PREDEFINED_QUERIES["total_sales"]["rows"]


def test_marks_the_dispatched_task_completed_without_touching_others():
    plan = {
        "tasks": [
            {"id": "t1", "description": "total sales", "executor": "query_execution_tool", "depends_on": [], "status": "PENDING"},
            {"id": "t2", "description": "sum it", "executor": "calculation_agent", "depends_on": ["t1"], "status": "PENDING"},
        ]
    }
    state = {"question": "q", "plan": plan}

    update = query_execution_tool_node(state)

    tasks_by_id = {t["id"]: t for t in update["plan"]["tasks"]}
    assert tasks_by_id["t1"]["status"] == "COMPLETED"
    assert tasks_by_id["t2"]["status"] == "PENDING"


def test_falls_back_to_default_query_when_no_keyword_matches():
    state = {"question": "q", "plan": _plan_with_query_task("some completely novel phrasing")}

    update = query_execution_tool_node(state)

    assert update["raw_rows"] == PREDEFINED_QUERIES["total_sales"]["rows"]


def test_raises_when_no_pending_query_task_exists():
    plan = {
        "tasks": [
            {"id": "t1", "description": "d", "executor": "query_execution_tool", "depends_on": [], "status": "COMPLETED"}
        ]
    }
    state = {"question": "q", "plan": plan}

    with pytest.raises(ValueError):
        query_execution_tool_node(state)


def test_custom_query_runner_is_used_when_provided():
    calls = []

    def fake_runner(query_key):
        calls.append(query_key)
        return [{"fake": True}]

    state = {"question": "q", "plan": _plan_with_query_task("by region breakdown")}
    update = query_execution_tool_node(state, run_query=fake_runner)

    assert calls == ["sales_by_region"]
    assert update["raw_rows"] == [{"fake": True}]
