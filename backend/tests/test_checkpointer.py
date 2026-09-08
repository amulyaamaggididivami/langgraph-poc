"""Unit + integration tests for TASK-ORCHESTRATION-013 (PostgresSaver
checkpointing).

Covers TEST-ORCHESTRATION-009. The connection-string resolution logic is
pure and unit-tested directly; `build_checkpointer()` itself needs a
real Postgres to connect to, so that test is skipped (not faked) when
one isn't reachable — a mock here would only prove psycopg's own API is
called correctly, not that `.setup()` actually creates real tables or
that checkpoints actually persist, which is the entire point of this
task.
"""

import asyncio

import psycopg
import pytest

from app.persistence.checkpointer import _conn_string, build_checkpointer


def test_conn_string_prefers_database_url_when_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h:5432/d")
    monkeypatch.delenv("DB_HOST", raising=False)

    assert _conn_string() == "postgresql://u:p@h:5432/d"


def test_conn_string_composes_from_db_parts_when_database_url_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "eb-local-poc")
    monkeypatch.setenv("DB_USER", "postgres")
    monkeypatch.setenv("DB_PASSWORD", "postgres")

    assert _conn_string() == "postgresql://postgres:postgres@localhost:5432/eb-local-poc"


def test_conn_string_raises_when_neither_available(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)

    with pytest.raises(KeyError, match="DB_HOST"):
        _conn_string()


def _postgres_reachable(conn_string: str) -> bool:
    try:
        with psycopg.connect(conn_string, connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


_TEST_CONN_STRING = "postgresql://postgres:postgres@localhost:5432/eb-local-poc"
_reachable = _postgres_reachable(_TEST_CONN_STRING)


@pytest.mark.skipif(not _reachable, reason="no reachable local Postgres at eb-local-poc")
def test_build_checkpointer_creates_tables_and_persists_a_checkpoint():
    # TEST-ORCHESTRATION-009
    async def run():
        checkpointer = await build_checkpointer(conn_string=_TEST_CONN_STRING)
        try:
            config = {"configurable": {"thread_id": "test-checkpointer-persistence", "checkpoint_ns": ""}}
            checkpoint = {
                "v": 1,
                "id": "1",
                "ts": "2026-09-08T00:00:00+00:00",
                "channel_values": {},
                "channel_versions": {},
                "versions_seen": {},
            }
            await checkpointer.aput(config, checkpoint, {"source": "input", "step": -1, "parents": {}}, {})

            return await checkpointer.aget_tuple(config)
        finally:
            # build_checkpointer() opens its own AsyncConnectionPool per
            # call — closing it here matters: an unclosed pool's
            # background worker task is left running inside this call's
            # asyncio.run() loop, which then hangs when that loop closes
            # (confirmed directly: SIGINT on a hung suite run showed the
            # worker stuck in `await q.get()`, then `Event loop is
            # closed` when it tried to respond to cancellation).
            await checkpointer.conn.close()

    stored = asyncio.run(run())
    assert stored is not None
    assert stored.checkpoint["id"] == "1"
