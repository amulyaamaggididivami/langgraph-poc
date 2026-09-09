"""Requests-table repository (trd.md §Data Model / §Persistence
Constraints) — backs every `requests.state` transition the Request
Lifecycle names in trd.md §State Machines.

A separate, small connection pool from the checkpointer's: the
checkpointer's `AsyncConnectionPool` (app/persistence/checkpointer.py)
is `langgraph-checkpoint-postgres`'s own private implementation detail,
not something this project's own queries should reach into, even
though both point at the same `synergy` Postgres instance (decision-30).

This module owns the module-level pool as a lazily-created singleton
(`_get_pool`) rather than taking one as a constructor argument, because
every call site (graph nodes, the future `/review` route) needs the
exact same pool without threading it through every function signature —
the same trade-off FastAPI's own dependency-injection system exists to
avoid; a POC-sized module doesn't need that machinery.
"""

from typing import Optional

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.persistence.db import resolve_conn_string

_pool: Optional[AsyncConnectionPool] = None


async def _get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=resolve_conn_string(),
            max_size=10,
            open=False,
            kwargs={"row_factory": dict_row},
        )
        await _pool.open()
    return _pool


async def insert_received(thread_id: str, question_text: str) -> None:
    """`— -> Received`, or a return to `Received` for a thread that
    already has a row: `thread_id` is one whole chat conversation, not
    one question (see graph.py's module docstring), so a second real
    turn on the same thread is expected here, not just an HTTP-layer
    retry of the same POST. `ON CONFLICT DO UPDATE` overwrites
    `question_text`/`state`/`decline_reason` with this new cycle's
    values — otherwise the `requests` table would keep showing turn 1's
    question and terminal state forever, even while a genuinely new
    turn is in flight."""
    pool = await _get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO requests (thread_id, question_text) VALUES (%s, %s) "
            "ON CONFLICT (thread_id) DO UPDATE SET "
            "question_text = EXCLUDED.question_text, state = 'Received', "
            "decline_reason = NULL, updated_at = now()",
            (thread_id, question_text),
        )


async def update_state(thread_id: str, state: str, *, decline_reason: Optional[str] = None) -> None:
    """Every other transition in the Request Lifecycle — `BeingAnalyzed`,
    `Declined` (with `decline_reason`), `AwaitingReview`, `Delivered`,
    `Withheld`. `decline_reason` defaults to `NULL`, matching every
    non-`Declined` transition; the table's own `CHECK` constraint
    (`decline_reason_only_when_declined`) is the actual enforcement,
    not this function."""
    pool = await _get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE requests SET state = %s, decline_reason = %s, updated_at = now() "
            "WHERE thread_id = %s",
            (state, decline_reason, thread_id),
        )


async def get_request(thread_id: str) -> Optional[dict]:
    pool = await _get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute("SELECT * FROM requests WHERE thread_id = %s", (thread_id,))
        return await cur.fetchone()


async def get_pending_reviews() -> list[dict]:
    """Backs `iface-review-api`'s pending list (TASK-ORCHESTRATION-015),
    served by `idx_requests_awaiting_review` (TASK-ORCHESTRATION-016)."""
    pool = await _get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT thread_id, question_text, updated_at FROM requests "
            "WHERE state = 'AwaitingReview' ORDER BY updated_at ASC"
        )
        return await cur.fetchall()
