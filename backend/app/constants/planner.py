"""Constants for the Planner node (TASK-ORCHESTRATION-003) — the closed
value sets behind `Task`/`PlannerOutput`'s Literal fields. The system
prompt lives in app/prompts/planner.py instead, not here.
"""

from typing import Literal

Executor = Literal["query_execution_tool", "calculation_agent"]

TaskStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]

# Open question per trd.md — this set may prove to need revisiting once
# real Planner behavior is observed (see docs/.../tasks.md Open Questions).
DeclineReason = Literal["unmatched_intent", "ambiguous_query", "out_of_scope"]
