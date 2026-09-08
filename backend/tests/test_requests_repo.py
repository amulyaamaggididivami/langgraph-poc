"""Integration tests for the requests-table repo (backing
TASK-ORCHESTRATION-014's `AwaitingReview` write, TASK-ORCHESTRATION-016's
pending-list query, and the `Received`/`BeingAnalyzed`/`Declined`
writes trd.md assigns to the `/chat` route). Real Postgres only — a
mock here would only prove psycopg's API is called correctly, not that
the CHECK constraint, the partial index, or the actual round trip work.
Skipped (not faked) when no local Postgres is reachable.
"""

import uuid

import psycopg
import pytest

from app.persistence import requests_repo


def _postgres_reachable(conn_string: str) -> bool:
    try:
        with psycopg.connect(conn_string, connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


_TEST_CONN_STRING = "postgresql://postgres:postgres@localhost:5432/eb-local-poc"
_reachable = _postgres_reachable(_TEST_CONN_STRING)

pytestmark = pytest.mark.skipif(not _reachable, reason="no reachable local Postgres at eb-local-poc")


@pytest.fixture(autouse=True)
async def _use_test_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_CONN_STRING)
    # each test gets its own pool against the env just set
    requests_repo._pool = None
    yield
    # Closing matters, not just discarding the reference: an unclosed
    # AsyncConnectionPool leaves its background worker task running
    # inside this test's event loop, which then hangs the *next* test
    # run's loop-teardown — confirmed directly (SIGINT on a hung suite
    # showed the worker stuck in `await q.get()` on a pool nothing ever
    # closed).
    if requests_repo._pool is not None:
        await requests_repo._pool.close()
    requests_repo._pool = None


@pytest.mark.anyio
async def test_insert_received_then_update_to_awaiting_review():
    thread_id = str(uuid.uuid4())

    await requests_repo.insert_received(thread_id, "what were total sales last month?")
    row = await requests_repo.get_request(thread_id)
    assert row["state"] == "Received"
    assert row["question_text"] == "what were total sales last month?"

    await requests_repo.update_state(thread_id, "BeingAnalyzed")
    row = await requests_repo.get_request(thread_id)
    assert row["state"] == "BeingAnalyzed"

    await requests_repo.update_state(thread_id, "AwaitingReview")
    row = await requests_repo.get_request(thread_id)
    assert row["state"] == "AwaitingReview"


@pytest.mark.anyio
async def test_declined_state_carries_its_reason():
    thread_id = str(uuid.uuid4())
    await requests_repo.insert_received(thread_id, "what's the weather?")

    await requests_repo.update_state(thread_id, "Declined", decline_reason="out_of_scope")

    row = await requests_repo.get_request(thread_id)
    assert row["state"] == "Declined"
    assert row["decline_reason"] == "out_of_scope"


@pytest.mark.anyio
async def test_check_constraint_rejects_decline_reason_without_declined_state():
    # TEST-ORCHESTRATION-003 — enforced by the table itself, not this repo
    thread_id = str(uuid.uuid4())
    await requests_repo.insert_received(thread_id, "irrelevant")

    with pytest.raises(psycopg.errors.CheckViolation):
        await requests_repo.update_state(thread_id, "BeingAnalyzed", decline_reason="out_of_scope")


@pytest.mark.anyio
async def test_get_pending_reviews_returns_only_awaiting_review_rows():
    awaiting_id = str(uuid.uuid4())
    delivered_id = str(uuid.uuid4())

    await requests_repo.insert_received(awaiting_id, "awaiting question")
    await requests_repo.update_state(awaiting_id, "AwaitingReview")

    await requests_repo.insert_received(delivered_id, "already delivered question")
    await requests_repo.update_state(delivered_id, "AwaitingReview")
    await requests_repo.update_state(delivered_id, "Delivered")

    pending = await requests_repo.get_pending_reviews()
    pending_ids = {row["thread_id"] for row in pending}

    assert awaiting_id in {str(t) for t in pending_ids}
    assert delivered_id not in {str(t) for t in pending_ids}


@pytest.mark.anyio
async def test_insert_received_is_idempotent_for_the_same_thread_id():
    thread_id = str(uuid.uuid4())

    await requests_repo.insert_received(thread_id, "first text")
    await requests_repo.insert_received(thread_id, "second text — should be ignored")

    row = await requests_repo.get_request(thread_id)
    assert row["question_text"] == "first text"
