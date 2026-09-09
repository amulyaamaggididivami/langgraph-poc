"""TASK-ORCHESTRATION-003: Planner node.

comp-planner (trd.md §Architecture Overview) — a structured-output LLM
call producing either a Plan or a Decline, never both
(invariant-decline-no-plan). The Planner only plans; it never executes
a tool itself (BRD decision-01).

Deliberate division of labor (2026-09-08 PTL direction, final form):
the Planner carries only domain knowledge (this is a clinic
appointments business) and tool knowledge (query_execution_tool vs
calculation_agent) — it does NOT know the specific fixed questions the
Query Execution Tool actually has. Matching a question to one of the
real predefined queries (or declining if nothing fits) is entirely the
Query Execution Tool's job (app/graph/nodes/query_tool.py), which
matches against `state["question"]` — the literal original text the
human asked, not a Planner-authored restatement of it. `Task` has no
`question` field of its own for this reason: routing a match through
something the Planner wrote in its own words, when the actual original
question already sits in state, was an unnecessary indirection. Two
earlier designs — the Planner picking a closed `query_key` enum, then
the Planner copying one of 4 exact question strings verbatim, then the
Planner writing its own free-text `Task.question` — are all superseded.

The Planner sees only the current turn's `state["question"]`, not
`state["messages"]`/conversation history — tried passing the full
history in for cross-turn follow-up resolution ("what about 2024" after
a prior "revenue by clinic" question), then reverted: a bare follow-up
still couldn't be usefully acted on downstream (`query_tool.py` matches
deterministic keyword overlap with no LLM of its own, so it declines on
a bare follow-up regardless of whether the Planner understood it), so
the added complexity wasn't earning its keep. A follow-up question is
currently expected to be self-contained, or to decline.
"""

import logging
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, model_validator

from app.constants.planner import DeclineReason, Executor, TaskStatus
from app.graph.llm import get_llm
from app.graph.state import OrchestratorState
from app.graph.timeout import with_timeout
from app.prompts.planner import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class Task(BaseModel):
    id: str
    description: str
    executor: Executor
    depends_on: list[str] = Field(default_factory=list)
    status: TaskStatus = "PENDING"


class Plan(BaseModel):
    tasks: list[Task]


class PlannerOutput(BaseModel):
    """Structured-output schema for the Planner LLM call. Exactly one of
    `plan`/`decline_reason` is set — enforced here, not left to the
    prompt (invariant-decline-no-plan)."""

    plan: Optional[Plan] = None
    decline_reason: Optional[DeclineReason] = None

    @model_validator(mode="after")
    def _exactly_one(self) -> "PlannerOutput":
        if (self.plan is None) == (self.decline_reason is None):
            raise ValueError(
                "PlannerOutput must set exactly one of plan/decline_reason "
                "(invariant-decline-no-plan)"
            )
        return self


def _default_llm() -> BaseChatModel:
    return get_llm()


def planner_node(state: OrchestratorState, llm: Optional[BaseChatModel] = None) -> dict:
    """LangGraph node: reads `state["question"]`, returns a partial state
    update containing either `plan` or `decline_reason` — never both keys
    at once, satisfying `invariant-decline-no-plan` at the state level
    too (not just inside `PlannerOutput`)."""
    llm = llm or _default_llm()
    structured_llm = llm.with_structured_output(PlannerOutput)

    # TASK-ORCHESTRATION-018: bounded to decision-24's 50s iface-llm-provider deadline.
    result: PlannerOutput = with_timeout(
        structured_llm.invoke,
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=state["question"]),
        ],
    )

    if result.plan is not None:
        tasks = result.plan.tasks
        logger.info(
            "planner: question=%r -> plan with %d task(s): %s",
            state["question"],
            len(tasks),
            [(t.id, t.executor, t.description) for t in tasks],
        )
        return {"plan": result.plan.model_dump()}

    logger.info(
        "planner: question=%r -> declined (%s)",
        state["question"],
        result.decline_reason,
    )
    return {"decline_reason": result.decline_reason}
