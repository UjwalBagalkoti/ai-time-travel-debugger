"""Minimal LangChain integration example."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sdk"))

from agent_tracer import AgentTracer
from integrations.langchain import TimeTravelCallback
from langchain_core.runnables import RunnableLambda


def lookup_order(value):
    return {"order_id": value["order_id"], "amount": 120, "refundable": True}


tracer = AgentTracer("langchain-demo", "examples/langchain_demo.trace")
callback = TimeTravelCallback(tracer)

chain = RunnableLambda(lookup_order)
result = chain.invoke(
    {"order_id": "992"},
    config={"callbacks": [callback]},
)

print(result)
print(f"Trace written to {tracer.output_path}")
