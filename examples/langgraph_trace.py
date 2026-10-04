"""Minimal LangGraph integration example."""

import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk"))

from agent_tracer import AgentTracer
from integrations.langgraph import LangGraphCallback
from langgraph.graph import END, START, StateGraph


class RefundState(TypedDict, total=False):
    order_id: str
    amount: int
    refundable: bool
    decision: str


def lookup_order(state: RefundState) -> RefundState:
    return {"amount": 120, "refundable": True}


def decide(state: RefundState) -> RefundState:
    return {"decision": "approve" if state["refundable"] else "reject"}


graph = StateGraph(RefundState)
graph.add_node("lookup_order", lookup_order)
graph.add_node("decide", decide)
graph.add_edge(START, "lookup_order")
graph.add_edge("lookup_order", "decide")
graph.add_edge("decide", END)
app = graph.compile()

tracer = AgentTracer("langgraph-demo", "examples/langgraph_demo.trace")
result = app.invoke(
    {"order_id": "992"},
    config={"callbacks": [LangGraphCallback(tracer)]},
)

print(result)
print(f"Trace written to {tracer.output_path}")
