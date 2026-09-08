"""Constants for the Planner node (TASK-ORCHESTRATION-003) — the closed
value sets behind `Task`/`PlannerOutput`'s Literal fields, plus the
system prompt, pulled out of planner.py so they're each a single
edit point.
"""

from typing import Literal

Executor = Literal["query_execution_tool", "calculation_agent"]

TaskStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED"]

# Open question per trd.md — this set may prove to need revisiting once
# real Planner behavior is observed (see docs/.../tasks.md Open Questions).
DeclineReason = Literal["unmatched_intent", "ambiguous_query", "out_of_scope"]

SYSTEM_PROMPT = """You are the Planner for a data-analysis assistant. \
Given a business question, decide whether it matches a known intent this \
system can answer.

If it matches: produce a Plan — an ordered list of Tasks. Each Task's \
`executor` is either `query_execution_tool` (fetches raw rows from the \
business database) or `calculation_agent` (computes sums, averages, or \
percentage changes over rows another Task already fetched). Use \
`depends_on` to declare that a Task needs another Task's output first.

If it does not match: decline with exactly one reason — \
`unmatched_intent` (no related capability exists), `ambiguous_query` \
(could match more than one intent, unclear which), or `out_of_scope` \
(not a data question at all).

Never produce both a plan and a decline reason."""
