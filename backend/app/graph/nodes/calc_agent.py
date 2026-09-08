"""TASK-ORCHESTRATION-006: Calculation Agent node.

comp-calc-agent (trd.md §Technology Choices) — a deepagents.create_deep_agent()
graph with real aggregation tool functions. Its state schema is
`messages`/`todos`/`files` — it shares no field names with
`OrchestratorState`, so registering it directly as a node would
silently pass no data in and receive no data back (verified directly:
two LangGraph state schemas only exchange a field when both sides
declare the same field name). `make_calc_agent_node` below is a
translation wrapper, not the "manual `.invoke()` with the config
silently dropped" anti-pattern decision-29 warns against — forwarding
the `config` LangGraph hands the node to `calc_agent.invoke()` was
verified (via `InMemorySaver`, before TASK-ORCHESTRATION-008 wired this
in) to still produce one checkpoint per internal tool call, nested
under this thread's own checkpoint history, exactly like true direct
registration does. Verifying that same property against a real
`PostgresSaver` is TASK-ORCHESTRATION-013.

Tool functions themselves live in app/tools/calculator/ (one per file);
see that package's docstring for the two BRD-named aggregation types
that don't have a tool here yet.
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from deepagents import create_deep_agent

from app.graph.llm import get_llm
from app.graph.state import OrchestratorState
from app.graph.timeout import with_timeout
from app.prompts.calc_agent import SYSTEM_PROMPT
from app.tools.calculator import TOOLS


def build_calc_agent(llm: Optional[BaseChatModel] = None) -> CompiledStateGraph:
    """Builds the Calculation Agent subgraph. Deliberately no checkpointer
    argument here — per decision-29, this must be compiled with none of
    its own so it inherits whichever PostgresSaver the parent graph
    (TASK-ORCHESTRATION-008) is compiled with when this is registered
    directly as a node."""
    llm = llm or get_llm()
    return create_deep_agent(model=llm, tools=TOOLS, system_prompt=SYSTEM_PROMPT)


def _find_pending_task(tasks: list[dict], executor: str) -> Optional[dict]:
    for task in tasks:
        if task["executor"] == executor and task["status"] == "PENDING":
            return task
    return None


def make_calc_agent_node(calc_agent: CompiledStateGraph):
    """Wraps a compiled Calculation Agent (real `build_calc_agent()` output,
    or a fake with a compatible `.invoke()` in tests) into a plain
    OrchestratorState node function. See module docstring for why this is
    a translation wrapper rather than direct registration."""

    def calc_agent_node(state: OrchestratorState, config: RunnableConfig) -> dict:
        plan = state["plan"]
        tasks = [dict(t) for t in plan["tasks"]]
        task = _find_pending_task(tasks, "calculation_agent")
        if task is None:
            raise ValueError(
                "calc_agent_node called with no PENDING calculation_agent Task in the plan"
            )

        prompt = (
            f"Task: {task['description']}\n"
            f"Raw rows: {state.get('raw_rows')}\n"
            f"Prior calculations: {state.get('calculations')}"
        )
        # TASK-ORCHESTRATION-018: bounded to decision-24's 30s iface-llm-provider deadline.
        result = with_timeout(calc_agent.invoke, {"messages": [HumanMessage(content=prompt)]}, config)
        answer = result["messages"][-1].content
        task["status"] = "COMPLETED"

        return {"plan": {**plan, "tasks": tasks}, "calculations": {"answer": answer}}

    return calc_agent_node
