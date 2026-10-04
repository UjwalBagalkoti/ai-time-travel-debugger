"""LangGraph integration for AI Time-Travel Debugger.

LangGraph runs every node through LangChain's callback system, so this reuses
the LangChain callback and only labels node runs as ``graph_node`` steps.
"""

from __future__ import annotations

from typing import Any

try:
    import langgraph  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "LangGraph integration requires langgraph. "
        "Install it with: pip install -r sdk/requirements-langgraph.txt"
    ) from exc

from .langchain import TimeTravelCallback


class LangGraphCallback(TimeTravelCallback):
    """Record LangGraph graph and node execution in an AgentTracer trace."""

    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any) -> None:
        metadata = kwargs.get("metadata") or {}
        node = metadata.get("langgraph_node")
        # Node runs are named after the node; anything else (the graph itself,
        # routers, chains called inside a node) is recorded as a regular chain.
        if node is None or kwargs.get("name") != node:
            return super().on_chain_start(serialized, inputs, **kwargs)
        self._start(
            kwargs.get("run_id"),
            "graph_node",
            {"node": node, "step": metadata.get("langgraph_step"), "inputs": inputs},
            kwargs.get("parent_run_id"),
            {"tags": kwargs.get("tags"), "metadata": metadata},
        )
