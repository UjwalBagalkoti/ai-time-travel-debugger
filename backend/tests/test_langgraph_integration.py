import json
import sys
from pathlib import Path
from typing import TypedDict

import pytest

SDK_ROOT = Path(__file__).resolve().parents[2] / "sdk"
sys.path.insert(0, str(SDK_ROOT))

pytest.importorskip("langgraph")

from langgraph.graph import END, START, StateGraph

from agent_tracer import AgentTracer
from integrations.langgraph import LangGraphCallback


class State(TypedDict):
    n: int


def add_one(state: State) -> State:
    return {"n": state["n"] + 1}


def double(state: State) -> State:
    if state["n"] > 5:
        raise ValueError("too big")
    return {"n": state["n"] * 2}


def build_graph():
    graph = StateGraph(State)
    graph.add_node("add_one", add_one)
    graph.add_node("double", double)
    graph.add_edge(START, "add_one")
    graph.add_edge("add_one", "double")
    graph.add_edge("double", END)
    return graph.compile()


def run(tmp_path, n):
    tracer = AgentTracer("graph-agent", str(tmp_path / "trace.json"))
    result = build_graph().invoke({"n": n}, config={"callbacks": [LangGraphCallback(tracer)]})
    return result, json.loads((tmp_path / "trace.json").read_text())["steps"]


def test_langgraph_records_nodes_under_graph(tmp_path):
    result, steps = run(tmp_path, 1)

    assert result == {"n": 4}
    graph, first, second = steps
    assert graph["step_type"] == "chain_execution"
    assert graph["input"]["name"] == "LangGraph"
    assert graph["output"] == {"n": 4}

    assert [first["input"]["node"], second["input"]["node"]] == ["add_one", "double"]
    assert [first["input"]["step"], second["input"]["step"]] == [1, 2]
    for node in (first, second):
        assert node["step_type"] == "graph_node"
        assert node["status"] == "completed"
        assert node["parent_step_id"] == graph["step_id"]
    assert first["input"]["inputs"] == {"n": 1}
    assert first["output"] == {"n": 2}
    assert second["output"] == {"n": 4}


def test_langgraph_records_failed_node(tmp_path):
    with pytest.raises(ValueError):
        run(tmp_path, 9)

    steps = json.loads((tmp_path / "trace.json").read_text())["steps"]
    failed = [s for s in steps if s["status"] == "failed"]
    assert {s["input"].get("node") or s["input"].get("name") for s in failed} == {"double", "LangGraph"}
    assert all(s["output"]["error"] == "too big" for s in failed)
