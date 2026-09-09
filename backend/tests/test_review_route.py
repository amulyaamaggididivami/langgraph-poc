"""Integration tests for TASK-ORCHESTRATION-015 (`/review` route).
Covers TEST-ORCHESTRATION-012, TEST-ORCHESTRATION-013.

Real Postgres only (skipped, not faked, when unreachable — same
reasoning as test_checkpointer.py/test_requests_repo.py): the whole
point of this route is resuming a real interrupted LangGraph run and
updating a real requests row, which a mock can't meaningfully verify.

Seeds a paused thread with a *separate* `build_graph()` call using fake
planner/synthesizer/calc_agent (no real LLM calls) against the same
real checkpointer+requests_repo the route under test uses. This works
because resuming past `approval_gate` never re-invokes the earlier
nodes — their results are already frozen in the checkpoint — so the
route's own internal graph (built with the real nodes, no overrides
exposed) never touches an LLM in these tests either.
"""

import uuid

import psycopg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.api.routes.review import register_review_route
from app.graph.graph import build_graph
from app.persistence import requests_repo
from app.schemas.review import ErrorResponse


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


def _fake_planner(with_calc_task=False):
    plan = {
        "tasks": [
            {
                "id": "t1",
                "description": "total sales",
                "executor": "query_execution_tool",
                "depends_on": [],
                "status": "PENDING",
            }
        ]
    }

    def planner(state):
        return {"plan": plan}

    return planner


def _fake_synthesizer(state):
    return {"synthesized_response": "the fake answer"}


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
        max_size=5,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    await pool.open()
    saver = AsyncPostgresSaver(pool)
    await saver.setup()
    yield saver
    await pool.close()


@pytest.fixture
async def app_client(checkpointer):
    app = FastAPI()
    register_review_route(app, checkpointer=checkpointer)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _seed_awaiting_review(checkpointer, thread_id: str, question: str) -> None:
    """Runs a fake-nodes graph far enough to pause at approval_gate,
    writing a real `AwaitingReview` row and a real interrupted
    checkpoint — everything the route under test needs, with no LLM
    call."""
    graph = build_graph(
        checkpointer=checkpointer,
        planner=_fake_planner(),
        synthesizer=_fake_synthesizer,
        calc_agent=_FakeCalcAgent(),
    )
    config = {"configurable": {"thread_id": thread_id}}
    await graph.ainvoke({"question": question}, config)


async def test_pending_list_excludes_a_resolved_thread(checkpointer, app_client):
    # Real Postgres is shared, persistent state across this whole suite
    # (not a per-test transaction) — other test files' own AwaitingReview
    # rows may already exist here, so this asserts exclusion for one
    # specific thread this test controls, not "the table is empty".
    thread_id = str(uuid.uuid4())
    await _seed_awaiting_review(checkpointer, thread_id, "total sales question")
    await app_client.post(f"/review/{thread_id}/decision", json={"decision": "approve"})

    response = await app_client.post("/review", json={})

    assert response.status_code == 200
    ids = {row["thread_id"] for row in response.json()}
    assert thread_id not in ids


async def test_pending_list_includes_a_seeded_awaiting_review_thread(checkpointer, app_client):
    thread_id = str(uuid.uuid4())
    await _seed_awaiting_review(checkpointer, thread_id, "total sales question")

    response = await app_client.post("/review", json={})

    assert response.status_code == 200
    ids = {row["thread_id"] for row in response.json()}
    assert thread_id in ids


async def test_approve_resumes_and_marks_delivered(checkpointer, app_client):
    thread_id = str(uuid.uuid4())
    await _seed_awaiting_review(checkpointer, thread_id, "total sales question")

    response = await app_client.post(f"/review/{thread_id}/decision", json={"decision": "approve"})

    assert response.status_code == 200
    assert "RUN_FINISHED" in response.text
    row = await requests_repo.get_request(thread_id)
    assert row["state"] == "Delivered"


async def test_reject_resumes_and_marks_withheld(checkpointer, app_client):
    thread_id = str(uuid.uuid4())
    await _seed_awaiting_review(checkpointer, thread_id, "total sales question")

    response = await app_client.post(f"/review/{thread_id}/decision", json={"decision": "reject"})

    assert response.status_code == 200
    row = await requests_repo.get_request(thread_id)
    assert row["state"] == "Withheld"


async def test_second_decision_on_the_same_thread_is_already_decided(checkpointer, app_client):
    # TEST-ORCHESTRATION-013 / TRD-ORCHESTRATION-006
    thread_id = str(uuid.uuid4())
    await _seed_awaiting_review(checkpointer, thread_id, "total sales question")
    first = await app_client.post(f"/review/{thread_id}/decision", json={"decision": "approve"})
    assert first.status_code == 200

    second = await app_client.post(f"/review/{thread_id}/decision", json={"decision": "approve"})

    assert second.status_code == 409
    body = second.json()
    assert body["code"] == "already_decided"


async def test_second_decision_never_touches_the_graph_or_the_row_again(checkpointer, app_client):
    # TEST-ORCHESTRATION-013's "not a duplicate SSE delivery": the second
    # attempt is rejected by the requests-table state check alone, before
    # ever resuming the graph again — proven by the row staying byte-for-byte
    # unchanged (including updated_at) across the rejected second call,
    # not just by checking the HTTP status of the second call.
    thread_id = str(uuid.uuid4())
    await _seed_awaiting_review(checkpointer, thread_id, "total sales question")
    await app_client.post(f"/review/{thread_id}/decision", json={"decision": "approve"})

    row_before = await requests_repo.get_request(thread_id)

    second = await app_client.post(f"/review/{thread_id}/decision", json={"decision": "reject"})

    row_after = await requests_repo.get_request(thread_id)
    assert second.status_code == 409
    assert row_after["state"] == row_before["state"] == "Delivered"  # unchanged — reject never applied
    assert row_after["updated_at"] == row_before["updated_at"]


async def test_decision_on_an_unknown_thread_is_not_found(app_client):
    response = await app_client.post(
        f"/review/{uuid.uuid4()}/decision", json={"decision": "approve"}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_pending_list_returns_shared_error_schema_on_db_failure(app_client, monkeypatch):
    # TEST-ORCHESTRATION-016: /review's failure path was previously
    # unhandled — a DB error fell through to FastAPI's own default
    # {"detail": ...} 500 body, not this project's shared error schema.
    async def _boom():
        raise RuntimeError("connection to synergy Postgres lost")

    monkeypatch.setattr(requests_repo, "get_pending_reviews", _boom)

    response = await app_client.post("/review", json={})

    assert response.status_code == 500
    ErrorResponse(**response.json())  # raises if the shape doesn't match
    assert response.json()["code"] == "internal_error"


async def test_all_three_error_triggers_share_the_same_schema(checkpointer, app_client, monkeypatch):
    # TEST-ORCHESTRATION-016: one failure trigger per endpoint on the
    # /review surface, all validated against the same ErrorResponse model.
    thread_id = str(uuid.uuid4())
    await _seed_awaiting_review(checkpointer, thread_id, "total sales question")
    await app_client.post(f"/review/{thread_id}/decision", json={"decision": "approve"})

    already_decided = await app_client.post(f"/review/{thread_id}/decision", json={"decision": "approve"})
    not_found = await app_client.post(f"/review/{uuid.uuid4()}/decision", json={"decision": "approve"})

    async def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(requests_repo, "get_pending_reviews", _boom)
    internal_error = await app_client.post("/review", json={})

    for response in (already_decided, not_found, internal_error):
        ErrorResponse(**response.json())  # every one must validate against the same schema
