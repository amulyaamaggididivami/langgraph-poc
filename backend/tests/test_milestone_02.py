"""TASK-ORCHESTRATION-020: Milestone-02 integration check.

Fills the remaining gaps among the Week-2 Test IDs that no earlier test
file already covers: TEST-ORCHESTRATION-012 (partial index actually
used), TEST-ORCHESTRATION-018 (reject-then-retry is already_decided,
not just approve-then-retry), TEST-ORCHESTRATION-020 (a real end-to-end
decline for a plausible-but-unmatched business question),
TEST-ORCHESTRATION-021 (concurrent requests are isolated),
TEST-ORCHESTRATION-022 (a genuinely-waiting thread and a
crashed-and-restarted one are both correctly reported as paused via the
standard `get_state()` API — see that test's own docstring for why this
is the tested interpretation).

Real Postgres only, same reachability gate as the other integration
test files.
"""

import asyncio
import uuid

import psycopg
import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.graph.graph import build_graph
from app.graph.timeout import IntegrationTimeoutError
from app.persistence import requests_repo


def _postgres_reachable(conn_string: str) -> bool:
    try:
        with psycopg.connect(conn_string, connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


_TEST_CONN_STRING = "postgresql://postgres:postgres@localhost:5432/eb-local-poc"
_reachable = _postgres_reachable(_TEST_CONN_STRING)

pytestmark = [
    pytest.mark.skipif(not _reachable, reason="no reachable local Postgres at eb-local-poc"),
    pytest.mark.anyio,
]

_QUERY_ONLY_PLAN = {
    "tasks": [
        {"id": "t1", "description": "revenue", "executor": "query_execution_tool", "depends_on": [], "status": "PENDING"},
    ]
}


def _fake_planner():
    def planner(state):
        return {"plan": _QUERY_ONLY_PLAN}

    return planner


def _fake_synthesizer(state):
    return {"synthesized_response": f"Answering: {state['question']}"}


class _FakeCalcAgent:
    def invoke(self, input_, config):
        return {"messages": [type("Msg", (), {"content": "unused"})()]}


@pytest.fixture(autouse=True)
async def _use_test_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _TEST_CONN_STRING)
    requests_repo._pool = None
    yield
    if requests_repo._pool is not None:
        await requests_repo._pool.close()
    requests_repo._pool = None


@pytest.fixture
async def checkpointer():
    pool = AsyncConnectionPool(
        conninfo=_TEST_CONN_STRING,
        max_size=10,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    await pool.open()
    saver = AsyncPostgresSaver(pool)
    await saver.setup()
    yield saver
    await pool.close()


async def _seed_awaiting_review(checkpointer, thread_id: str, question: str) -> None:
    graph = build_graph(
        checkpointer=checkpointer,
        planner=_fake_planner(),
        synthesizer=_fake_synthesizer,
        calc_agent=_FakeCalcAgent(),
    )
    await graph.ainvoke({"question": question}, {"configurable": {"thread_id": thread_id}})


async def test_pending_list_query_uses_the_partial_index(checkpointer):
    # TEST-ORCHESTRATION-012
    thread_id = str(uuid.uuid4())
    await _seed_awaiting_review(checkpointer, thread_id, "total revenue question")

    pool = await requests_repo._get_pool()
    async with pool.connection() as conn:
        # Postgres's planner correctly prefers a sequential scan over any
        # index on a tiny table — a seq scan genuinely is cheaper there
        # (confirmed directly: this assertion failed against the ~20
        # incidental rows other tests happened to leave behind). A decoy
        # population makes the plan choice realistic, and the whole
        # insert is rolled back before this connection is released, so
        # nothing is ever actually committed to the shared table.
        await conn.execute(
            "INSERT INTO requests (thread_id, question_text, state) "
            "SELECT gen_random_uuid(), 'decoy', 'Delivered' FROM generate_series(1, 2000)"
        )
        await conn.execute("ANALYZE requests")
        cur = await conn.execute(
            "EXPLAIN SELECT thread_id, question_text, updated_at FROM requests "
            "WHERE state = 'AwaitingReview' ORDER BY updated_at ASC"
        )
        plan_lines = [row["QUERY PLAN"] for row in await cur.fetchall()]
        await conn.rollback()  # undo the decoy insert — never committed
    plan_text = "\n".join(plan_lines)

    assert "idx_requests_awaiting_review" in plan_text

    pending = await requests_repo.get_pending_reviews()
    # get_pending_reviews() returns raw psycopg rows — thread_id comes
    # back as a native uuid.UUID, not a str (review.py's own route
    # converts with str() before this ever reaches JSON; this direct
    # call bypasses that, so the test must too).
    assert any(str(row["thread_id"]) == thread_id for row in pending)


async def test_reject_then_retry_is_already_decided_not_just_approve_then_retry(checkpointer):
    # TEST-ORCHESTRATION-018 — the earlier already_decided regression
    # test only tried approve-then-approve; this closes the reject side.
    from httpx import ASGITransport, AsyncClient
    from fastapi import FastAPI

    from app.api.routes.review import register_review_route

    app = FastAPI()
    register_review_route(app, checkpointer=checkpointer)
    transport = ASGITransport(app=app)

    thread_id = str(uuid.uuid4())
    await _seed_awaiting_review(checkpointer, thread_id, "total revenue question")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(f"/review/{thread_id}/decision", json={"decision": "reject"})
        assert first.status_code == 200

        second = await client.post(f"/review/{thread_id}/decision", json={"decision": "approve"})

    assert second.status_code == 409
    assert second.json()["code"] == "already_decided"
    row = await requests_repo.get_request(thread_id)
    assert row["state"] == "Withheld"  # the reject stuck — the second attempt did not flip it to Delivered


async def test_decline_flow_produces_a_clean_message_no_partial_answer():
    # TEST-ORCHESTRATION-020 — real end-to-end: a plausible-sounding
    # business question with no matching predefined query. Real Planner
    # LLM call (this is the one test in this file that isn't fakes-only —
    # the whole point is proving the *real* decline path, not a fake one).
    graph = build_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = await graph.ainvoke({"question": "how many unique patients have we seen"}, config)

    assert "__interrupt__" not in result  # never reaches AwaitingReview
    assert result.get("decline_reason") is not None
    assert result.get("synthesized_response") is None  # no partial/guessed answer
    reply = result["messages"][-1].content
    assert result["decline_reason"] in reply

    row = await requests_repo.get_request(thread_id)
    assert row["state"] == "Declined"


async def test_concurrent_requests_are_isolated(checkpointer):
    # TEST-ORCHESTRATION-021
    failing_thread = str(uuid.uuid4())
    healthy_thread = str(uuid.uuid4())

    def failing_query_tool(state, run_query=None):
        raise IntegrationTimeoutError(seconds=50)

    def healthy_query_tool(state, run_query=None):
        plan = state["plan"]
        tasks = [dict(t) for t in plan["tasks"]]
        tasks[0]["status"] = "COMPLETED"
        return {"plan": {**plan, "tasks": tasks}, "raw_rows": [{"total": 1}]}

    failing_graph = build_graph(
        checkpointer=checkpointer,
        planner=_fake_planner(),
        query_tool=failing_query_tool,
        synthesizer=_fake_synthesizer,
        calc_agent=_FakeCalcAgent(),
    )
    healthy_graph = build_graph(
        checkpointer=checkpointer,
        planner=_fake_planner(),
        query_tool=healthy_query_tool,
        synthesizer=_fake_synthesizer,
        calc_agent=_FakeCalcAgent(),
    )

    results = await asyncio.gather(
        failing_graph.ainvoke({"question": "a failing question"}, {"configurable": {"thread_id": failing_thread}}),
        healthy_graph.ainvoke({"question": "a healthy question"}, {"configurable": {"thread_id": healthy_thread}}),
        return_exceptions=True,
    )

    failing_result, healthy_result = results
    assert isinstance(failing_result, IntegrationTimeoutError)
    assert "__interrupt__" in healthy_result  # the healthy one reached AwaitingReview normally

    failing_row = await requests_repo.get_request(failing_thread)
    healthy_row = await requests_repo.get_request(healthy_thread)
    assert failing_row["state"] == "BeingAnalyzed"  # never advanced past the failure
    assert healthy_row["state"] == "AwaitingReview"  # unaffected by the other thread's failure


async def test_genuine_wait_and_post_restart_wait_are_both_reported_as_resumable(checkpointer):
    # TEST-ORCHESTRATION-022. Interpretation, stated up front: per
    # trd.md's own state table, `Interrupted` has no side effect of its
    # own to write — "this is the *absence* of an expected event,
    # detected on restart, not an event this module emits itself" — so
    # a genuinely-waiting thread and a crashed-and-restarted one are
    # *expected* to look identical in the `requests` table (both simply
    # `AwaitingReview`). What must actually be true, and is proven here,
    # is that standard introspection (`graph.aget_state()`, not manual
    # checkpoint-table inspection) correctly reports *both* as paused
    # and resumable — the real thing TASK-ORCHESTRATION-019 already
    # demonstrated live for the post-restart case (a genuinely fresh OS
    # process resumed correctly); this test covers the never-crashed
    # case with the same assertion for direct comparison.
    thread_id = str(uuid.uuid4())
    await _seed_awaiting_review(checkpointer, thread_id, "total revenue question")

    graph = build_graph(checkpointer=checkpointer)  # fresh graph object, real nodes unused (never invoked on aget_state)
    state = await graph.aget_state({"configurable": {"thread_id": thread_id}})

    assert state.next == ("approval_gate",)
    assert len(state.interrupts) == 1
    row = await requests_repo.get_request(thread_id)
    assert row["state"] == "AwaitingReview"
