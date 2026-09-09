"""TASK-ORCHESTRATION-004/023: Query Execution Tool node.

comp-query-tool (trd.md §Architecture Overview) — deterministic, no
LLM. Dispatches one of BRD constraint-02's fixed predefined queries
(app/constants/query_tool.py) against the real `appointments` table and
returns raw rows. Read-only by construction: this module contains no
write statement, so constraint-01 holds regardless of which query runs
— a plain read-only connection, no ORM, no query builder.

`run_query` is bounded to decision-24's 30s deadline
(TASK-ORCHESTRATION-018) — this is the module's one `iface-business-db`
call site.

Division of labor (2026-09-08 PTL direction, final form): the Planner
only carries domain + tool knowledge — it doesn't know the 4 real
questions this node actually has. This node owns the whole "does a
predefined query answer this, and if not, decline" call, matching
against `state["question"]` — the literal original text the human
asked, not a Planner-authored restatement of it (an earlier version
matched a Planner-written `Task.question` instead; dropped as an
unnecessary indirection once the actual original question was already
sitting right there in state).

Matching (`_match_sql`) derives its signal from each entry's own
`question` string at match time — there is no separate hand-authored
keyword/stem list anywhere. For each of the 4 entries, its significant
words (stopwords stripped) are compared against the human's question,
word-for-word, using a shared-prefix check so morphological variants
match ("cancelled"/"cancellation" share a 6-character prefix; plain
`==` would miss that). The entry with the most matching words wins;
ties break on list order in PREDEFINED_QUERIES (earlier entries win —
this is why cancellation is listed before the more generic
appointment-count-by-month entry: a question can easily mention "number
of appointments" while actually asking about cancellations). No match
at all (best score 0) means no predefined query exists for it, and this
node declines rather than guessing.
"""

import logging
import re
from typing import Callable, Optional

import psycopg
from psycopg.rows import dict_row

from app.constants.query_tool import PREDEFINED_QUERIES
from app.graph.state import OrchestratorState
from app.graph.timeout import with_timeout
from app.persistence.db import resolve_conn_string

logger = logging.getLogger(__name__)

QueryRunner = Callable[[str], list]

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "what", "how", "many",
    "there", "by", "of", "and", "to", "in", "for", "that", "this", "from",
    "all", "on", "as", "it", "its", "with",
}


def _significant_words(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOPWORDS]


def _words_match(a: str, b: str) -> bool:
    # Shared-prefix check, not exact equality — lets morphological
    # variants match (e.g. "cancelled"/"cancellation" share "cancel";
    # "appointment"/"appointments" share the whole shorter word).
    threshold = min(len(a), len(b), 5)
    common = 0
    for x, y in zip(a, b):
        if x != y:
            break
        common += 1
    return common >= threshold


def _match_sql(question: str) -> Optional[str]:
    task_words = _significant_words(question)
    if not task_words:
        return None

    best_score = 0
    best_sql = None
    for entry in PREDEFINED_QUERIES:
        entry_words = _significant_words(entry["question"])
        score = sum(
            1 for ew in entry_words if any(_words_match(ew, tw) for tw in task_words)
        )
        if score > best_score:
            best_score = score
            best_sql = entry["sql"]

    return best_sql if best_score > 0 else None


def _default_runner(sql: str) -> list:
    with psycopg.connect(resolve_conn_string(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def _find_pending_task(tasks: list[dict]) -> Optional[dict]:
    for task in tasks:
        if task["executor"] == "query_execution_tool" and task["status"] == "PENDING":
            return task
    return None


def query_execution_tool_node(state: OrchestratorState, run_query: Optional[QueryRunner] = None) -> dict:
    """LangGraph node: finds the first PENDING `query_execution_tool` Task
    in `state["plan"]`, matches `state["question"]` (the human's actual
    original question) against the predefined queries, and either runs
    the match (marking the Task COMPLETED) or — on no match — marks it
    FAILED and declines the whole request."""
    run_query = run_query or _default_runner

    plan = state["plan"]
    tasks = [dict(t) for t in plan["tasks"]]
    task = _find_pending_task(tasks)
    logger.info("query_tool: task=%r", task)
    if task is None:
        raise ValueError(
            "query_execution_tool_node called with no PENDING query_execution_tool Task in the plan"
        )

    question = state["question"]
    sql = _match_sql(question)
    if sql is None:
        logger.warning(
            "query_tool: task_id=%r question=%r matched no predefined query — declining",
            task["id"],
            question,
        )
        task["status"] = "FAILED"
        return {
            "plan": {**plan, "tasks": tasks},
            "decline_reason": "unmatched_intent",
        }

    logger.info("query_tool: task_id=%r question=%r matched", task["id"], question)
    rows = with_timeout(run_query, sql)
    logger.info("query_tool: returned %d row(s)", len(rows))
    task["status"] = "COMPLETED"

    return {"plan": {**plan, "tasks": tasks}, "raw_rows": rows}
