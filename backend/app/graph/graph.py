"""Minimal LangGraph stub graph.

Replace the node logic with real chains/tools as the agent grows.
"""
from typing import TypedDict

from langgraph.graph import StateGraph, END


class GraphState(TypedDict):
    message: str
    reply: str


def echo_node(state: GraphState) -> GraphState:
    return {"reply": f"echo: {state['message']}"}


def build_graph():
    workflow = StateGraph(GraphState)
    workflow.add_node("echo", echo_node)
    workflow.set_entry_point("echo")
    workflow.add_edge("echo", END)
    return workflow.compile()


graph = build_graph()
