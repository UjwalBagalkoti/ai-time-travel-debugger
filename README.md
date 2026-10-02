# AI Time-Travel Debugger

Time-travel debugging and replay infrastructure for AI agents.

Record an agent execution once, inspect every step, rewind to a historical state, edit the trajectory, and fork a replay branch without accidentally re-running external tools.

## Architecture

- SDK: records agent/tool execution into JSON trace files.
- FastAPI backend: ingests traces, exposes step inspection and branching APIs, and persists replay state.
- Next.js + React Flow frontend: visual execution DAG, timeline, step inspector, and branch controls.
- PostgreSQL/SQLite persistence: PostgreSQL for deployed environments, SQLite for local development.
- Replay safety: recorded tool calls are served from cache on exact argument matches; unknown external calls are not silently executed.

## Quick start

```bash
docker-compose up --build
```

Open:

- http://localhost:3000 — debugger
- http://localhost:8000/docs — API docs

A demo trace is included under `examples/demo.trace`.

## LangChain integration

The SDK now includes an optional LangChain callback integration. It records LangChain chain, tool, and model lifecycle events into the same trace format used by the debugger.

Install the optional dependency:

```bash
pip install -r sdk/requirements.txt
pip install -r sdk/requirements-langchain.txt
```

Attach the callback to a LangChain runnable or agent:

```python
from agent_tracer import AgentTracer
from integrations.langchain import TimeTravelCallback

tracer = AgentTracer("my-langchain-agent")
callback = TimeTravelCallback(tracer)

result = chain.invoke(
    {"input": "hello"},
    config={"callbacks": [callback]},
)
```

The integration captures:

- chain execution inputs and outputs
- tool inputs and outputs
- LLM/model prompts and responses where LangChain exposes the callback
- execution status and latency
- parent/child relationships between nested LangChain runs
- tags and metadata supplied by LangChain

A deterministic example is available at `examples/langchain_trace.py`.

> Note: LangChain callback coverage depends on the runnable/model implementation. Some newer agent execution paths may intentionally bypass particular legacy callback events, so model-level capture should be verified for the specific LangChain stack being used.

## Why this exists

AI agents are difficult to debug because a failure may depend on an earlier model decision, tool result, or state mutation. Traditional logs tell you what happened; this project is designed around being able to go back to that point and explore an alternative execution path.

## Project structure

```
sdk/       Agent tracing SDK
backend/   FastAPI API + replay engine
frontend/  Next.js debugger UI
examples/  Sample execution traces and integrations
```

## Status

Early working implementation. The replay model and UI are intended as a foundation for deeper agent observability, deterministic tool replay, branching execution, and production hardening.
