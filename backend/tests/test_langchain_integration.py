import json
import sys
from pathlib import Path
from uuid import uuid4

import pytest

SDK_ROOT = Path(__file__).resolve().parents[2] / "sdk"
sys.path.insert(0, str(SDK_ROOT))

pytest.importorskip("langchain_core")

from agent_tracer import AgentTracer
from integrations.langchain import TimeTravelCallback


def test_langchain_callback_records_tool_step(tmp_path):
    tracer = AgentTracer("test-agent", str(tmp_path / "trace.json"))
    callback = TimeTravelCallback(tracer)

    run_id = uuid4()
    callback.on_tool_start(
        {"name": "lookup_order"},
        '{"order_id":"992"}',
        run_id=run_id,
    )
    callback.on_tool_end(
        {"amount": 120, "refundable": True},
        run_id=run_id,
    )

    payload = json.loads((tmp_path / "trace.json").read_text())
    assert len(payload["steps"]) == 1
    step = payload["steps"][0]
    assert step["step_type"] == "tool_execution"
    assert step["status"] == "completed"
    assert step["input"]["tool_name"] == "lookup_order"
    assert step["output"]["amount"] == 120


def test_langchain_callback_preserves_nested_parent(tmp_path):
    tracer = AgentTracer("test-agent", str(tmp_path / "trace.json"))
    callback = TimeTravelCallback(tracer)

    parent_id = uuid4()
    child_id = uuid4()

    callback.on_chain_start(
        {"name": "agent"},
        {"input": "refund order 992"},
        run_id=parent_id,
    )
    callback.on_tool_start(
        {"name": "lookup_order"},
        '{"order_id":"992"}',
        run_id=child_id,
        parent_run_id=parent_id,
    )
    callback.on_tool_end({"amount": 120}, run_id=child_id)
    callback.on_chain_end({"output": "done"}, run_id=parent_id)

    payload = json.loads((tmp_path / "trace.json").read_text())
    assert len(payload["steps"]) == 2
    assert payload["steps"][0]["step_type"] == "chain_execution"
    assert payload["steps"][1]["step_type"] == "tool_execution"
    assert payload["steps"][1]["parent_step_id"] == payload["steps"][0]["step_id"]
    assert payload["steps"][0]["status"] == "completed"


def test_langchain_callback_records_errors(tmp_path):
    tracer = AgentTracer("test-agent", str(tmp_path / "trace.json"))
    callback = TimeTravelCallback(tracer)

    run_id = uuid4()
    callback.on_tool_start({"name": "dangerous_tool"}, "{}", run_id=run_id)
    callback.on_tool_error(RuntimeError("blocked"), run_id=run_id)

    payload = json.loads((tmp_path / "trace.json").read_text())
    assert payload["steps"][0]["status"] == "failed"
    assert payload["steps"][0]["output"]["error"] == "blocked"
