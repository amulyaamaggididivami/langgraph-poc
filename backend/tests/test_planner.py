"""Unit tests for TASK-ORCHESTRATION-003 (Planner node).

Covers TEST-ORCHESTRATION-001, -002, -005. TEST-ORCHESTRATION-023
("Decline produces exactly one trace entry") needs the assembled graph
+ requests table and belongs at the integration layer, once
TASK-ORCHESTRATION-008 exists — not unit-testable against planner_node
alone.
"""

import pytest
from pydantic import ValidationError

from app.graph.nodes.planner import Plan, PlannerOutput, Task, planner_node


class _FakeStructuredLLM:
    """Stands in for `ChatGoogleGenerativeAI.with_structured_output(...)` —
    returns a fixed PlannerOutput regardless of the prompt."""

    def __init__(self, fixed_output: PlannerOutput):
        self._fixed_output = fixed_output

    def with_structured_output(self, schema):
        assert schema is PlannerOutput
        return self

    def invoke(self, messages):
        return self._fixed_output


def test_planner_produces_valid_plan_for_matching_question():
    # TEST-ORCHESTRATION-001
    fixed = PlannerOutput(
        plan=Plan(
            tasks=[
                Task(id="t1", description="fetch total revenue", executor="query_execution_tool"),
                Task(
                    id="t2",
                    description="sum rows",
                    executor="calculation_agent",
                    depends_on=["t1"],
                ),
            ]
        )
    )
    update = planner_node({"question": "total revenue last quarter"}, llm=_FakeStructuredLLM(fixed))

    assert "plan" in update
    assert "decline_reason" not in update
    tasks = update["plan"]["tasks"]
    assert all(t["executor"] in ("query_execution_tool", "calculation_agent") for t in tasks)


def test_planner_produces_decline_for_unmatched_question():
    # TEST-ORCHESTRATION-002
    fixed = PlannerOutput(decline_reason="unmatched_intent")
    update = planner_node({"question": "what's the weather"}, llm=_FakeStructuredLLM(fixed))

    assert update.get("decline_reason") == "unmatched_intent"
    assert "plan" not in update  # invariant-decline-no-plan


@pytest.mark.parametrize(
    "status",
    ["PENDING", "RUNNING", "COMPLETED", "FAILED"],
)
def test_task_status_is_always_one_of_four_values(status):
    # TEST-ORCHESTRATION-005 (property-based slice: valid values accepted)
    task = Task(id="t1", description="d", executor="query_execution_tool", status=status)
    assert task.status == status


def test_task_status_rejects_unknown_value():
    # TEST-ORCHESTRATION-005 (the other half: closed enum, nothing else)
    with pytest.raises(ValidationError):
        Task(id="t1", description="d", executor="query_execution_tool", status="BOGUS")


def test_new_task_defaults_to_pending():
    # TASK-ORCHESTRATION-003 acceptance: "Every Task.status starts PENDING"
    task = Task(id="t1", description="d", executor="query_execution_tool")
    assert task.status == "PENDING"


def test_planner_output_rejects_both_plan_and_decline():
    # invariant-decline-no-plan, enforced at construction
    with pytest.raises(ValidationError):
        PlannerOutput(
            plan=Plan(tasks=[Task(id="t1", description="d", executor="query_execution_tool")]),
            decline_reason="out_of_scope",
        )


def test_planner_output_rejects_neither_plan_nor_decline():
    with pytest.raises(ValidationError):
        PlannerOutput()
