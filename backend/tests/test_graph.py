"""Unit tests for TASK-ORCHESTRATION-008 (StateGraph wiring) and the
`requests`-table writes added to `extract_question`/`record_decline`/
`approval_gate` (originally TASK-ORCHESTRATION-009/014/016's job,
fixed here after testing found the table stayed empty through a real
run).

Covers TEST-ORCHESTRATION-007. Uses `InMemorySaver` (fast, no real
Postgres needed) and fakes for planner/calc_agent/synthesizer so no real
LLM call happens — real-Postgres checkpoint-sharing verification is
TASK-ORCHESTRATION-013's job, and real-Postgres requests-table
verification is `tests/test_requests_repo.py`'s, not this file's.

`extract_question`/`record_decline`/`approval_gate` are async now (they
await the requests-table repo), so every graph run here goes through
`_ainvoke` (`graph.ainvoke` under `asyncio.run`) — LangGraph's sync
`.invoke()` cannot run a graph containing any async node at all (raises
`TypeError` immediately), confirmed directly before converting this
file.
"""

import asyncio

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.graph.graph import build_graph
from app.graph.nodes.query_tool import query_execution_tool_node


def _ainvoke(graph, input_, config):
    return asyncio.run(graph.ainvoke(input_, config))


class _FakeRequestsRepo:
    """In-memory stand-in for `app.persistence.requests_repo` — same
    async method names, no real Postgres. Records every call so tests
    can assert on the exact sequence of writes, not just the final row."""

    def __init__(self):
        self.rows = {}
        self.calls = []

    async def insert_received(self, thread_id, question_text):
        self.calls.append(("insert_received", thread_id, question_text))
        self.rows[thread_id] = {"state": "Received", "question_text": question_text, "decline_reason": None}

    async def update_state(self, thread_id, state, *, decline_reason=None):
        self.calls.append(("update_state", thread_id, state, decline_reason))
        self.rows[thread_id]["state"] = state
        self.rows[thread_id]["decline_reason"] = decline_reason

    async def get_request(self, thread_id):
        return self.rows.get(thread_id)

    async def get_pending_reviews(self):
        return [
            {"thread_id": tid, "question_text": row["question_text"]}
            for tid, row in self.rows.items()
            if row["state"] == "AwaitingReview"
        ]


def _plan(with_calc_task: bool):
    tasks = [
        {
            "id": "t1",
            "description": "fetch revenue data",
            "executor": "query_execution_tool",
            "depends_on": [],
            "status": "PENDING",
        }
    ]
    if with_calc_task:
        tasks.append(
            {
                "id": "t2",
                "description": "sum the rows",
                "executor": "calculation_agent",
                "depends_on": ["t1"],
                "status": "PENDING",
            }
        )
    return {"tasks": tasks}


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeCalcAgent:
    """Stands in for `build_calc_agent()`'s compiled graph — a compatible
    `.invoke(input, config)`, recording the config it was called with so
    tests can confirm it was forwarded (the property that keeps
    checkpoint-sharing correct — see graph.py's module docstring)."""

    def __init__(self, answer="42"):
        self.answer = answer
        self.received_config = None
        self.call_count = 0

    def invoke(self, input_, config):
        self.call_count += 1
        self.received_config = config
        return {"messages": [_FakeMessage(self.answer)]}


def _make_fake_planner(plan=None, decline_reason=None):
    def fake_planner(state):
        if decline_reason is not None:
            return {"decline_reason": decline_reason}
        return {"plan": plan}

    return fake_planner


def _make_fake_synthesizer():
    captured = {}

    def fake_synthesizer(state):
        captured["state"] = dict(state)
        return {"synthesized_response": "here is your answer"}

    return fake_synthesizer, captured


def test_declined_question_skips_the_rest_of_the_pipeline():
    fake_calc_agent = _FakeCalcAgent()
    query_tool_calls = []

    def tracking_query_tool(state):
        query_tool_calls.append(state)
        return query_execution_tool_node(state)

    fake_synthesizer, synth_captured = _make_fake_synthesizer()

    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(decline_reason="unmatched_intent"),
        query_tool=tracking_query_tool,
        calc_agent=fake_calc_agent,
        synthesizer=fake_synthesizer,
        requests_repo=_FakeRequestsRepo(),
    )

    config = {"configurable": {"thread_id": "t-declined"}}
    result = _ainvoke(graph, {"question": "what's the weather"}, config)

    assert result["decline_reason"] == "unmatched_intent"
    assert query_tool_calls == []
    assert fake_calc_agent.call_count == 0
    assert "state" not in synth_captured


def test_plan_with_query_and_calc_task_runs_the_full_pipeline():
    # TEST-ORCHESTRATION-007
    fake_calc_agent = _FakeCalcAgent(answer="the sum is 476750")
    fake_synthesizer, synth_captured = _make_fake_synthesizer()

    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=_plan(with_calc_task=True)),
        calc_agent=fake_calc_agent,
        synthesizer=fake_synthesizer,
        requests_repo=_FakeRequestsRepo(),
    )

    config = {"configurable": {"thread_id": "t-full"}}
    result = _ainvoke(graph, {"question": "total sales, summed"}, config)

    # the dependent step (calc_agent) received the query tool's output
    assert fake_calc_agent.call_count == 1
    # the final step (synthesizer) received both upstream outputs
    assert synth_captured["state"]["raw_rows"] is not None
    assert synth_captured["state"]["calculations"] == {"answer": "the sum is 476750"}
    assert result["synthesized_response"] == "here is your answer"

    tasks = result["plan"]["tasks"]
    assert all(t["status"] == "COMPLETED" for t in tasks)


def test_plan_with_only_a_query_task_skips_the_calc_agent():
    fake_calc_agent = _FakeCalcAgent()
    fake_synthesizer, synth_captured = _make_fake_synthesizer()

    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=_plan(with_calc_task=False)),
        calc_agent=fake_calc_agent,
        synthesizer=fake_synthesizer,
        requests_repo=_FakeRequestsRepo(),
    )

    config = {"configurable": {"thread_id": "t-query-only"}}
    result = _ainvoke(graph, {"question": "list total sales rows"}, config)

    assert fake_calc_agent.call_count == 0
    assert synth_captured["state"]["raw_rows"] is not None
    assert synth_captured["state"].get("calculations") is None
    assert result["synthesized_response"] == "here is your answer"


def test_plan_with_only_a_calc_task_routes_directly_to_calc_agent():
    # e.g. "what is 2+3" — the numbers are already in the question, so the
    # Plan has no query_execution_tool task at all, only calculation_agent
    # with no depends_on. Must not be routed through query_tool first.
    plan = {
        "tasks": [
            {
                "id": "t1",
                "description": "calculate the sum of 2 and 3",
                "executor": "calculation_agent",
                "depends_on": [],
                "status": "PENDING",
            }
        ]
    }
    fake_calc_agent = _FakeCalcAgent(answer="5")
    fake_synthesizer, synth_captured = _make_fake_synthesizer()
    query_tool_calls = []

    def tracking_query_tool(state):
        query_tool_calls.append(state)
        return query_execution_tool_node(state)

    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=plan),
        query_tool=tracking_query_tool,
        calc_agent=fake_calc_agent,
        synthesizer=fake_synthesizer,
        requests_repo=_FakeRequestsRepo(),
    )

    config = {"configurable": {"thread_id": "t-calc-only"}}
    result = _ainvoke(graph, {"question": "what is 2+3"}, config)

    assert query_tool_calls == []
    assert fake_calc_agent.call_count == 1
    assert synth_captured["state"]["calculations"] == {"answer": "5"}
    assert synth_captured["state"].get("raw_rows") is None
    assert result["synthesized_response"] == "here is your answer"


def test_query_tool_decline_skips_calc_agent_and_synthesizer():
    # 2026-09-08: the Planner is now permissive about domain fit — the
    # Query Tool is the real gate, and can decline after a Plan already
    # exists. Uses the REAL query_execution_tool_node (not a fake) since
    # this is exactly the matching behavior under test — it matches
    # state["question"] below, not anything on the task itself.
    plan = {
        "tasks": [
            {
                "id": "t1",
                "description": "fetch inventory data",
                "executor": "query_execution_tool",
                "depends_on": [],
                "status": "PENDING",
            }
        ]
    }
    fake_calc_agent = _FakeCalcAgent()
    fake_synthesizer, synth_captured = _make_fake_synthesizer()

    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=plan),
        calc_agent=fake_calc_agent,
        synthesizer=fake_synthesizer,
        requests_repo=_FakeRequestsRepo(),
    )

    config = {"configurable": {"thread_id": "t-query-tool-decline"}}
    result = _ainvoke(graph, {"question": "what's our inventory situation"}, config)

    assert result["decline_reason"] == "unmatched_intent"
    assert result["plan"]["tasks"][0]["status"] == "FAILED"
    assert fake_calc_agent.call_count == 0
    assert "state" not in synth_captured
    assert "unmatched_intent" in result["messages"][-1].content


def test_chat_style_messages_input_is_translated_into_a_question():
    # TASK-ORCHESTRATION-009's boundary: ag-ui-langgraph only ever
    # supplies `messages`, never a bare `question`.
    captured = {}

    def fake_planner(state):
        captured["question"] = state["question"]
        return {"decline_reason": "unmatched_intent"}

    graph = build_graph(checkpointer=InMemorySaver(), planner=fake_planner, requests_repo=_FakeRequestsRepo())
    config = {"configurable": {"thread_id": "t-messages-in"}}
    _ainvoke(graph, {"messages": [HumanMessage(content="what's the weather")]}, config)

    assert captured["question"] == "what's the weather"


def test_finalize_appends_a_reply_message_on_decline():
    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(decline_reason="out_of_scope"),
        requests_repo=_FakeRequestsRepo(),
    )
    config = {"configurable": {"thread_id": "t-finalize-decline"}}
    result = _ainvoke(graph, {"question": "irrelevant"}, config)

    assert "out_of_scope" in result["messages"][-1].content


def test_finalize_appends_a_reply_message_on_success():
    # TASK-ORCHESTRATION-014: the synthesized-response path now pauses at
    # approval_gate before finalize runs, so this needs an approve resume.
    fake_synthesizer, _ = _make_fake_synthesizer()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=_plan(with_calc_task=False)),
        calc_agent=_FakeCalcAgent(),
        synthesizer=fake_synthesizer,
        requests_repo=_FakeRequestsRepo(),
    )
    config = {"configurable": {"thread_id": "t-finalize-success"}}
    _ainvoke(graph, {"question": "total sales"}, config)
    result = _ainvoke(graph, Command(resume={"decision": "approve"}), config)

    assert result["messages"][-1].content == "here is your answer"


def test_approval_gate_pauses_the_run_until_resumed():
    fake_synthesizer, _ = _make_fake_synthesizer()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=_plan(with_calc_task=False)),
        calc_agent=_FakeCalcAgent(),
        synthesizer=fake_synthesizer,
        requests_repo=_FakeRequestsRepo(),
    )
    config = {"configurable": {"thread_id": "t-awaiting-review"}}
    result = _ainvoke(graph, {"question": "total sales"}, config)

    assert "__interrupt__" in result
    assert graph.get_state(config).next == ("approval_gate",)
    # no reply message exists yet — finalize has not run
    assert result.get("messages") in (None, [])


def test_reject_resumes_to_withheld_message():
    fake_synthesizer, _ = _make_fake_synthesizer()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=_plan(with_calc_task=False)),
        calc_agent=_FakeCalcAgent(),
        synthesizer=fake_synthesizer,
        requests_repo=_FakeRequestsRepo(),
    )
    config = {"configurable": {"thread_id": "t-rejected"}}
    _ainvoke(graph, {"question": "total sales"}, config)
    result = _ainvoke(graph, Command(resume={"decision": "reject"}), config)

    assert result["human_approval"] == "rejected"
    assert "withheld" in result["messages"][-1].content.lower()


def test_declined_question_never_reaches_the_approval_gate():
    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(decline_reason="out_of_scope"),
        requests_repo=_FakeRequestsRepo(),
    )
    config = {"configurable": {"thread_id": "t-decline-no-gate"}}
    result = _ainvoke(graph, {"question": "irrelevant"}, config)

    assert "__interrupt__" not in result
    assert graph.get_state(config).next == ()


def test_calc_agent_receives_the_run_config_for_checkpoint_inheritance():
    fake_calc_agent = _FakeCalcAgent()
    fake_synthesizer, _ = _make_fake_synthesizer()

    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=_plan(with_calc_task=True)),
        calc_agent=fake_calc_agent,
        synthesizer=fake_synthesizer,
        requests_repo=_FakeRequestsRepo(),
    )

    config = {"configurable": {"thread_id": "t-config-forward"}}
    _ainvoke(graph, {"question": "total sales, summed"}, config)

    assert fake_calc_agent.received_config["configurable"]["thread_id"] == "t-config-forward"


def test_requests_table_sees_received_then_being_analyzed_then_awaiting_review():
    fake_synthesizer, _ = _make_fake_synthesizer()
    repo = _FakeRequestsRepo()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=_plan(with_calc_task=False)),
        calc_agent=_FakeCalcAgent(),
        synthesizer=fake_synthesizer,
        requests_repo=repo,
    )
    config = {"configurable": {"thread_id": "t-requests-happy-path"}}
    _ainvoke(graph, {"question": "total sales"}, config)

    row = repo.rows["t-requests-happy-path"]
    assert row["question_text"] == "total sales"
    assert row["state"] == "AwaitingReview"

    state_sequence = [call[2] for call in repo.calls if call[0] == "update_state"]
    assert state_sequence[0] == "BeingAnalyzed"
    assert "AwaitingReview" in state_sequence


def test_requests_table_records_decline_with_its_reason():
    repo = _FakeRequestsRepo()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(decline_reason="ambiguous_query"),
        requests_repo=repo,
    )
    config = {"configurable": {"thread_id": "t-requests-decline"}}
    _ainvoke(graph, {"question": "irrelevant"}, config)

    row = repo.rows["t-requests-decline"]
    assert row["state"] == "Declined"
    assert row["decline_reason"] == "ambiguous_query"


def test_requests_table_never_reaches_awaiting_review_on_decline():
    repo = _FakeRequestsRepo()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(decline_reason="out_of_scope"),
        requests_repo=repo,
    )
    config = {"configurable": {"thread_id": "t-requests-decline-no-review"}}
    _ainvoke(graph, {"question": "irrelevant"}, config)

    states_seen = {call[2] for call in repo.calls if call[0] == "update_state"}
    assert "AwaitingReview" not in states_seen
