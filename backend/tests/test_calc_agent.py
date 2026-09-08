"""Unit/integration tests for TASK-ORCHESTRATION-006 (Calculation Agent).

Covers TEST-ORCHESTRATION-004 and -014. TASK-ORCHESTRATION-005's spike
already proved real-Postgres checkpoint sharing generically; -014 here
uses an in-memory checkpointer to check the same property against the
real tool set, not to re-prove Postgres sharing itself.
"""

from typing import Annotated

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolCall
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.graph.nodes.calc_agent import build_calc_agent
from app.tools.calculator import average, count_values, percentage_change


class _ToolBindingFakeChatModel(FakeMessagesListChatModel):
    """See TASK-ORCHESTRATION-005 spike finding: the base fake model has
    no bind_tools(), which deepagents' agent loop always calls first."""

    def bind_tools(self, tools, **kwargs):
        return self


def test_average_and_percentage_change_are_correct():
    assert average([10, 20, 30]) == 20


def test_count_values_counts_raw_rows_not_just_numbers():
    # "how many appointments" needs to count query-tool row dicts, not a
    # pre-extracted numeric list.
    rows = [{"appointment_id": "A101"}, {"appointment_id": "A102"}, {"appointment_id": "A103"}]
    assert count_values(rows) == 3
    assert percentage_change(50, 75) == 50.0


def test_calc_agent_selects_correct_tool_for_an_average_task():
    # TEST-ORCHESTRATION-004
    fake_llm = _ToolBindingFakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="average", args={"numbers": [10, 20, 30]}, id="c1")],
            ),
            AIMessage(content="The average is 20."),
        ]
    )
    agent = build_calc_agent(llm=fake_llm)

    result = agent.invoke(
        {"messages": [HumanMessage(content="What's the average of 10, 20, 30?")]}
    )

    tool_messages = [m for m in result["messages"] if getattr(m, "name", None) == "average"]
    assert len(tool_messages) == 1
    assert tool_messages[0].content == "20.0"


def test_calc_agent_tool_calls_checkpoint_individually():
    # TEST-ORCHESTRATION-014 (chained ratio-style task: two tool calls)
    fake_llm = _ToolBindingFakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="average", args={"numbers": [10, 20]}, id="c1")],
            ),
            AIMessage(
                content="",
                tool_calls=[ToolCall(name="average", args={"numbers": [30, 50]}, id="c2")],
            ),
            AIMessage(content="Old average 15, new average 40."),
        ]
    )
    calc_agent = build_calc_agent(llm=fake_llm)

    class ParentState(TypedDict):
        messages: Annotated[list, add_messages]

    parent = StateGraph(ParentState)
    parent.add_node("calc", calc_agent)
    parent.add_edge(START, "calc")
    parent.add_edge("calc", END)

    checkpointer = MemorySaver()
    compiled = parent.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "test-thread"}}
    compiled.invoke({"messages": [HumanMessage(content="compare the two periods")]}, config)

    history = list(compiled.get_state_history(config))
    assert len(history) >= 2

    try:
        list(calc_agent.get_state_history(config))
        raise AssertionError("subgraph should have no independent checkpoint store")
    except ValueError:
        pass  # "No checkpointer set" — confirms it shares the parent's
