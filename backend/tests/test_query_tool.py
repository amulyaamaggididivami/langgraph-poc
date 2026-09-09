"""Unit + integration tests for TASK-ORCHESTRATION-004/023 (Query
Execution Tool node).

Covers TEST-ORCHESTRATION-008. The "no write statement" half of that
Test ID's acceptance criteria is a static property of this module (it
contains no INSERT/UPDATE/DELETE and no business-DB write call) rather
than something to assert at runtime.

2026-09-08 (final form): matching is against `state["question"]` — the
human's literal original question — not anything the Planner writes.
`Task` carries no `question` field of its own.
"""

import pytest

from app.graph.nodes.query_tool import _default_runner, _match_sql, query_execution_tool_node
from app.persistence.db import resolve_conn_string


def _pending_query_task():
    return {
        "tasks": [
            {
                "id": "t1",
                "description": "fetch data",
                "executor": "query_execution_tool",
                "depends_on": [],
                "status": "PENDING",
            }
        ]
    }


def test_dispatches_when_the_original_question_matches_a_predefined_query():
    # TEST-ORCHESTRATION-008
    calls = []

    def fake_runner(sql):
        calls.append(sql)
        return [{"fake": True}]

    state = {"question": "what is the total revenue this quarter", "plan": _pending_query_task()}
    update = query_execution_tool_node(state, run_query=fake_runner)

    assert len(calls) == 1
    assert "paid_amount" in calls[0]  # ran the overall-revenue SQL
    assert update["raw_rows"] == [{"fake": True}]


def test_marks_the_dispatched_task_completed_without_touching_others():
    plan = {
        "tasks": [
            {"id": "t1", "description": "d", "executor": "query_execution_tool", "depends_on": [], "status": "PENDING"},
            {"id": "t2", "description": "sum it", "executor": "calculation_agent", "depends_on": ["t1"], "status": "PENDING"},
        ]
    }
    state = {"question": "what is the total revenue", "plan": plan}

    update = query_execution_tool_node(state, run_query=lambda sql: [])

    tasks_by_id = {t["id"]: t for t in update["plan"]["tasks"]}
    assert tasks_by_id["t1"]["status"] == "COMPLETED"
    assert tasks_by_id["t2"]["status"] == "PENDING"


def test_declines_when_the_original_question_matches_no_predefined_query():
    # 2026-09-08: no default fallback — a question with no matching
    # predefined query declines here, not with a wrong-guess answer.
    calls = []
    state = {"question": "check inventory stock levels", "plan": _pending_query_task()}

    update = query_execution_tool_node(state, run_query=lambda sql: calls.append(sql) or [])

    assert calls == []  # no query ever ran
    assert update["decline_reason"] == "unmatched_intent"
    assert update["plan"]["tasks"][0]["status"] == "FAILED"


def test_cancellation_beats_the_generic_appointment_overlap():
    # Priority tie-break: this question scores equally against the
    # month-breakdown entry ("appointments" overlaps) and the
    # cancellation entry ("cancelled" shares "cancel" with
    # "cancellation") — cancellation must win the tie since it's listed
    # first in PREDEFINED_QUERIES.
    calls = []
    state = {
        "question": "what is the total number of appointments and the total number of cancelled appointments",
        "plan": _pending_query_task(),
    }

    query_execution_tool_node(state, run_query=lambda sql: calls.append(sql) or [])

    assert len(calls) == 1
    assert "status" in calls[0]  # ran the cancellation-rate SQL


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

    def fake_runner(sql):
        calls.append(sql)
        return [{"fake": True}]

    state = {"question": "what is the revenue by clinic breakdown", "plan": _pending_query_task()}
    update = query_execution_tool_node(state, run_query=fake_runner)

    assert len(calls) == 1
    assert "clinic_name" in calls[0]
    assert update["raw_rows"] == [{"fake": True}]


def _synergy_reachable() -> bool:
    try:
        import psycopg

        with psycopg.connect(resolve_conn_string(), connect_timeout=2):
            return True
    except Exception:
        return False


@pytest.mark.skipif(not _synergy_reachable(), reason="real synergy Postgres instance not reachable")
class TestAgainstRealAppointmentsData:
    """TASK-ORCHESTRATION-023 acceptance: each predefined query runs
    against the real seeded schema and returns expected rows — not a
    fixture. Values checked here were verified by hand against the live
    `appointments` table (27,560 rows) before writing this test."""

    def test_appointment_count_by_month_returns_ten_months(self):
        sql = _match_sql("how many appointments per month")
        rows = _default_runner(sql)
        assert len(rows) == 10
        assert sum(r["appointment_count"] for r in rows) == 27560

    def test_overall_revenue_matches_known_total(self):
        sql = _match_sql("what is the total revenue")
        rows = _default_runner(sql)
        assert len(rows) == 1
        assert rows[0]["appointment_count"] == 27560
        assert float(rows[0]["total_paid"]) == 18283106.0

    def test_revenue_by_clinic_normalizes_duplicate_clinic_names(self):
        sql = _match_sql("revenue by clinic")
        rows = _default_runner(sql)
        clinic_names = {r["clinic_name"] for r in rows}
        # 5 real clinics, not 10 — proves the ', ' normalization collapsed
        # the comma-variant duplicates from the live data.
        assert len(clinic_names) == 5
        assert all(", " not in name for name in clinic_names)

    def test_cancellation_rate_covers_all_four_statuses(self):
        sql = _match_sql("cancellation rate")
        rows = _default_runner(sql)
        statuses = {r["status"] for r in rows}
        assert statuses == {"CNF", "PCANCEL", "NOSHOW", "DCANCEL"}
