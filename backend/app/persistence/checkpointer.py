"""TASK-ORCHESTRATION-013: Wire PostgresSaver checkpointing.

comp-checkpoint-store (trd.md §Persistence Constraints) — a thin wrapper
around langgraph-checkpoint-postgres's `AsyncPostgresSaver` (decision-23),
not custom persistence code. Builds a long-lived connection pool
(appropriate for a server process — `AsyncPostgresSaver.from_conn_string`'s
own async-contextmanager form closes its connection when the `async
with` block exits, which fits a short script, not something meant to
stay open for a FastAPI app's whole lifetime) and runs `.setup()` once,
which creates LangGraph's own checkpoint tables (`checkpoints`,
`checkpoint_blobs`, `checkpoint_writes`) if they don't already exist —
nobody hand-writes DDL for these (trd.md §Architecture Overview).

Async, not the sync `PostgresSaver`: `ag-ui-langgraph`'s `LangGraphAgent`
drives the compiled graph through its async methods (`aget_state`,
`astream`, ...) for `/chat`'s SSE endpoint — confirmed directly, a sync
`PostgresSaver` wired into that path raises `NotImplementedError` from
`BaseCheckpointSaver.aget_tuple()` the moment a request comes in, not at
import or startup time. A script driving the graph synchronously (like
this project's own verification scripts, or a future `/review` handler
built the same way) works fine against either; the FastAPI route is
what forces the async requirement here.

`autocommit=True, prepare_threshold=0, row_factory=dict_row` on every
pooled connection are not stylistic choices — they're
`AsyncPostgresSaver`'s own documented requirement (verified directly
against `AsyncPostgresSaver.from_conn_string`'s source); it fails
silently/oddly without them.
"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.persistence.db import resolve_conn_string

# Re-exported under its old name — tests/other callers imported this
# directly before the resolver moved to db.py (shared with
# requests_repo.py).
_conn_string = resolve_conn_string


async def build_checkpointer(conn_string: str | None = None) -> AsyncPostgresSaver:
    """Builds an `AsyncPostgresSaver` backed by a long-lived connection
    pool and runs `.setup()` once. The caller owns the pool's lifetime —
    there is no corresponding `close()` here because a POC has exactly
    one long-lived pool for the process's whole life (`app/main.py`'s
    lifespan), not a per-request open/close cycle."""
    pool = AsyncConnectionPool(
        conninfo=conn_string or _conn_string(),
        max_size=20,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    return checkpointer
