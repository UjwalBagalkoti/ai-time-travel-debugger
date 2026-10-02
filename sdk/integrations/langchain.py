"""LangChain callback integration for AI Time-Travel Debugger."""

from __future__ import annotations

from typing import Any

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError as exc:
    raise ImportError(
        "LangChain integration requires langchain-core. "
        "Install it with: pip install -r sdk/requirements-langchain.txt"
    ) from exc

from ..agent_tracer import AgentTracer


class TimeTravelCallback(BaseCallbackHandler):
    """Record LangChain chains, tools, and model calls in an AgentTracer trace."""

    def __init__(self, tracer: AgentTracer):
        super().__init__()
        self.tracer = tracer
        self._runs: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _key(run_id: Any) -> str:
        return str(run_id)

    @staticmethod
    def _name(serialized: dict[str, Any] | None, fallback: str) -> str:
        if not serialized:
            return fallback
        name = serialized.get("name")
        if name:
            return str(name)
        identifier = serialized.get("id")
        if isinstance(identifier, list) and identifier:
            return str(identifier[-1])
        if identifier:
            return str(identifier)
        return fallback

    def _start(
        self,
        run_id: Any,
        step_type: str,
        input_data: Any,
        parent_run_id: Any = None,
        metadata: dict | None = None,
    ):
        parent = self._runs.get(self._key(parent_run_id)) if parent_run_id else None
        step_id = self.tracer.start_step(
            step_type=step_type,
            input_data=input_data,
            parent_step_id=parent.get("step_id") if parent else None,
            metadata=metadata,
        )
        self._runs[self._key(run_id)] = {"step_id": step_id}

    def _finish(
        self,
        run_id: Any,
        output: Any = None,
        status: str = "completed",
        error: Any = None,
    ):
        run = self._runs.pop(self._key(run_id), None)
        if run:
            return self.tracer.finish_step(
                run["step_id"], output=output, status=status, error=error
            )
        return None

    def on_chain_start(self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any) -> None:
        self._start(
            kwargs.get("run_id"),
            "chain_execution",
            {"name": self._name(serialized, "chain"), "inputs": inputs},
            kwargs.get("parent_run_id"),
            {"tags": kwargs.get("tags"), "metadata": kwargs.get("metadata")},
        )

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        self._finish(kwargs.get("run_id"), outputs)

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        self._finish(kwargs.get("run_id"), status="failed", error=error)

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        tool_input = kwargs.get("inputs", input_str)
        self._start(
            kwargs.get("run_id"),
            "tool_execution",
            {"tool_name": self._name(serialized, "tool"), "input": tool_input},
            kwargs.get("parent_run_id"),
            {"tags": kwargs.get("tags"), "metadata": kwargs.get("metadata")},
        )

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        self._finish(kwargs.get("run_id"), output)

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        self._finish(kwargs.get("run_id"), status="failed", error=error)

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        invocation = kwargs.get("invocation_params") or {}
        self._start(
            kwargs.get("run_id"),
            "llm_call",
            {
                "model": invocation.get("model_name") or invocation.get("model"),
                "prompts": prompts,
            },
            kwargs.get("parent_run_id"),
            {"tags": kwargs.get("tags"), "metadata": kwargs.get("metadata")},
        )

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        self._finish(
            kwargs.get("run_id"),
            {
                "generations": getattr(response, "generations", None),
                "llm_output": getattr(response, "llm_output", None),
            },
        )

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        self._finish(kwargs.get("run_id"), status="failed", error=error)

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        **kwargs: Any,
    ) -> None:
        invocation = kwargs.get("invocation_params") or {}
        self._start(
            kwargs.get("run_id"),
            "llm_call",
            {
                "model": invocation.get("model_name") or invocation.get("model"),
                "messages": messages,
                "name": self._name(serialized, "chat_model"),
            },
            kwargs.get("parent_run_id"),
            {"tags": kwargs.get("tags"), "metadata": kwargs.get("metadata")},
        )
