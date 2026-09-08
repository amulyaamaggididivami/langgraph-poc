"""Unit tests for TASK-ORCHESTRATION-008 (StateGraph wiring).

Covers TEST-ORCHESTRATION-007. Uses `InMemorySaver` (fast, no real
Postgres needed) and fakes for planner/calc_agent/synthesizer so no real
LLM call happens — real-Postgres checkpoint-sharing verification is
TASK-ORCHESTRATION-013's job, not this one's.
"""

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.graph.graph import build_graph
from app.graph.nodes.query_tool import query_execution_tool_node


def _plan(with_calc_task: bool):
    tasks = [
        {
            "id": "t1",
            "description": "total sales",
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
    )

    config = {"configurable": {"thread_id": "t-declined"}}
    result = graph.invoke({"question": "what's the weather"}, config)

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
    )

    config = {"configurable": {"thread_id": "t-full"}}
    result = graph.invoke({"question": "total sales, summed"}, config)

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
    )

    config = {"configurable": {"thread_id": "t-query-only"}}
    result = graph.invoke({"question": "list total sales rows"}, config)

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
    )

    config = {"configurable": {"thread_id": "t-calc-only"}}
    result = graph.invoke({"question": "what is 2+3"}, config)

    assert query_tool_calls == []
    assert fake_calc_agent.call_count == 1
    assert synth_captured["state"]["calculations"] == {"answer": "5"}
    assert synth_captured["state"].get("raw_rows") is None
    assert result["synthesized_response"] == "here is your answer"


def test_chat_style_messages_input_is_translated_into_a_question():
    # TASK-ORCHESTRATION-009's boundary: ag-ui-langgraph only ever
    # supplies `messages`, never a bare `question`.
    captured = {}

    def fake_planner(state):
        captured["question"] = state["question"]
        return {"decline_reason": "unmatched_intent"}

    graph = build_graph(checkpointer=InMemorySaver(), planner=fake_planner)
    config = {"configurable": {"thread_id": "t-messages-in"}}
    graph.invoke({"messages": [HumanMessage(content="what's the weather")]}, config)

    assert captured["question"] == "what's the weather"


def test_finalize_appends_a_reply_message_on_decline():
    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(decline_reason="out_of_scope"),
    )
    config = {"configurable": {"thread_id": "t-finalize-decline"}}
    result = graph.invoke({"question": "irrelevant"}, config)

    assert "out_of_scope" in result["messages"][-1].content


def test_finalize_appends_a_reply_message_on_success():
    fake_synthesizer, _ = _make_fake_synthesizer()
    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=_plan(with_calc_task=False)),
        calc_agent=_FakeCalcAgent(),
        synthesizer=fake_synthesizer,
    )
    config = {"configurable": {"thread_id": "t-finalize-success"}}
    result = graph.invoke({"question": "total sales"}, config)

    assert result["messages"][-1].content == "here is your answer"


def test_calc_agent_receives_the_run_config_for_checkpoint_inheritance():
    fake_calc_agent = _FakeCalcAgent()
    fake_synthesizer, _ = _make_fake_synthesizer()

    graph = build_graph(
        checkpointer=InMemorySaver(),
        planner=_make_fake_planner(plan=_plan(with_calc_task=True)),
        calc_agent=fake_calc_agent,
        synthesizer=fake_synthesizer,
    )

    config = {"configurable": {"thread_id": "t-config-forward"}}
    graph.invoke({"question": "total sales, summed"}, config)

    assert fake_calc_agent.received_config["configurable"]["thread_id"] == "t-config-forward"
