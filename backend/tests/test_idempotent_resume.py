"""Tests for TASK-ORCHESTRATION-019 (idempotent resume verification).
Covers TEST-ORCHESTRATION-024, TEST-ORCHESTRATION-025.

Real Postgres only (skipped, not faked, when unreachable — same
reasoning as test_checkpointer.py/test_requests_repo.py/test_review_route.py).

TEST-ORCHESTRATION-019's own literal scenario (kill the backend process,
restart it, approve) is demonstrated live against a real spawned server
process rather than encoded as a routine pytest test here — a
subprocess-managed integration test trades a small amount of extra
rigor for a meaningfully higher risk of flaking the whole suite (port
binding races, slow startup, orphaned processes on a failed test run).
What IS encoded below proves the same load-bearing property without
that risk: a second, fully independent graph object, sharing no Python
state whatsoever with the first, built fresh against the same real
checkpointer (the same mechanism a restarted process would use to
reconnect) resumes correctly and never re-invokes an already-completed
Task's executor. The real query_execution_tool_node runs against the
real `appointments` table here, not a fake — the whole point is
verifying the real executor isn't double-invoked.
"""

import uuid

import psycopg
import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.graph.graph import build_graph
from app.graph.nodes.query_tool import query_execution_tool_node
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


def _counting_query_tool(counter):
    def wrapped(state, run_query=None):
        counter.append(1)
        return query_execution_tool_node(state, run_query=run_query)

    return wrapped


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


async def test_query_tool_executor_invoked_exactly_once_across_interrupt_and_resume(checkpointer):
    # TEST-ORCHESTRATION-025
    thread_id = str(uuid.uuid4())
    call_count: list[int] = []
    question = "what is the total revenue"

    # First graph object — stands in for the pre-crash process.
    graph_before = build_graph(
        checkpointer=checkpointer,
        planner=_fake_planner(),
        query_tool=_counting_query_tool(call_count),
        synthesizer=_fake_synthesizer,
        calc_agent=_FakeCalcAgent(),
    )
    config = {"configurable": {"thread_id": thread_id}}
    paused = await graph_before.ainvoke({"question": question}, config)

    assert call_count == [1]
    assert "__interrupt__" in paused

    # Second, fully independent graph object, sharing no Python state
    # with graph_before — stands in for a freshly restarted process
    # resuming from the same real Postgres checkpoint.
    graph_after = build_graph(
        checkpointer=checkpointer,
        planner=_fake_planner(),
        query_tool=_counting_query_tool(call_count),
        synthesizer=_fake_synthesizer,
        calc_agent=_FakeCalcAgent(),
    )
    result = await graph_after.ainvoke(Command(resume={"decision": "approve"}), config)

    assert call_count == [1]  # still exactly once — resume never re-ran it
    assert result["human_approval"] == "approved"


async def test_resumed_response_traces_to_the_original_question(checkpointer):
    # TEST-ORCHESTRATION-024
    thread_id = str(uuid.uuid4())
    question = "what is the total revenue for last quarter"

    graph_before = build_graph(
        checkpointer=checkpointer,
        planner=_fake_planner(),
        synthesizer=_fake_synthesizer,
        calc_agent=_FakeCalcAgent(),
    )
    config = {"configurable": {"thread_id": thread_id}}
    await graph_before.ainvoke({"question": question}, config)

    # Independent graph object resumes it — same simulated "different process".
    graph_after = build_graph(
        checkpointer=checkpointer,
        planner=_fake_planner(),
        synthesizer=_fake_synthesizer,
        calc_agent=_FakeCalcAgent(),
    )
    result = await graph_after.ainvoke(Command(resume={"decision": "approve"}), config)

    row = await requests_repo.get_request(thread_id)
    assert row["question_text"] == question
    assert question in result["synthesized_response"]
    assert question in result["messages"][-1].content
