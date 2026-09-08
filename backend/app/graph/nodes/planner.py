"""TASK-ORCHESTRATION-003: Planner node.

comp-planner (trd.md §Architecture Overview) — a structured-output LLM
call producing either a Plan or a Decline, never both
(invariant-decline-no-plan). The Planner only plans; it never executes
a tool itself (BRD decision-01).
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, model_validator

from app.constants.planner import DeclineReason, Executor, TaskStatus
from app.graph.llm import get_llm
from app.graph.state import OrchestratorState
from app.graph.timeout import with_timeout
from app.prompts.planner import SYSTEM_PROMPT


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

    # TASK-ORCHESTRATION-018: bounded to decision-24's 30s iface-llm-provider deadline.
    result: PlannerOutput = with_timeout(
        structured_llm.invoke,
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=state["question"]),
        ],
    )

    if result.plan is not None:
        return {"plan": result.plan.model_dump()}
    return {"decline_reason": result.decline_reason}
