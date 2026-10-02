# AI Time-Travel Debugger

**Your AI agent failed 7 steps ago. Rewind it instead of rerunning everything.**

Time-travel debugging and replay infrastructure for AI agents.

Record an agent execution once, inspect every step, rewind to a historical state, edit the trajectory, and fork a replay branch without accidentally re-running external tools.

> **Core idea:** Logs tell you what happened. Time-travel debugging lets you explore what would have happened if you changed an earlier decision.

## 🚀 See it in action

**Live debugger:** https://ai-time-travel-debugger.onrender.com

**API:** https://ai-time-travel-debugger-api.onrender.com/docs

The fastest way to understand the project is to load the included demo trace and try the timeline, step inspector, and **Fork & Replay Branch** workflow.

## What it does

```
Agent execution
      ↓
LLM → tool → LLM → tool → LLM
      ↓
     FAIL
      ↓
Rewind → inspect → change trajectory → fork → replay
```

The debugger lets you:

- record LLM and tool execution steps
- capture inputs, outputs, state snapshots, latency, and token information
- visualize an execution as a graph
- scrub through the execution timeline
- inspect individual historical steps
- rewind to an earlier point
- create a separate replay branch
- replay recorded tool calls when their arguments match
- block unknown external calls during replay

## Why this exists

AI agents are difficult to debug because a failure may depend on an earlier model decision, tool result, or state mutation.

A typical execution might look like:

**LLM → search → LLM → database → tool → LLM → final response**

If the final response is wrong, the useful mistake may have happened several steps earlier. Re-running the whole agent can also repeat expensive calls or external side effects.

This project explores a different debugging workflow:

**Record once → inspect history → rewind → change → fork → replay.**

## Architecture

- **SDK:** records agent/tool execution into JSON trace files.
- **FastAPI backend:** ingests traces, exposes step inspection and branching APIs, and persists replay state.
- **Next.js + React Flow frontend:** visual execution DAG, timeline, step inspector, and branch controls.
- **PostgreSQL/SQLite persistence:** PostgreSQL for deployed environments, SQLite for local development.
- **Replay safety:** recorded tool calls are served from cache on exact argument matches; unknown external calls are not silently executed.

## Quick start

```bash
docker-compose up --build
```

Open:

- http://localhost:3000 — debugger
- http://localhost:8000/docs — API docs

A demo trace is included under `examples/demo.trace`.

## LangChain integration

The SDK includes an optional LangChain callback integration. It records LangChain chain, tool, and model lifecycle events into the same trace format used by the debugger.

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

## 🧪 Try a real agent failure

A useful next step is to run an agent with several dependent steps, intentionally create a failure, and ask:

> **What state would I need to change to reproduce the correct outcome without starting from zero?**

That is the problem this debugger is designed to explore.

If you build agents with LangChain, LangGraph, custom Python tooling, or similar runtimes, feedback on what should be captured for deterministic reproduction is especially useful.

## 🤝 Contributing

This project is intentionally being built as an open developer tool. If you work on AI agents, tracing, replay systems, or developer tooling, contributions are welcome.

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) for development and integration guidelines.

### Good starting points

- **LangGraph integration** — add optional graph/node execution tracing.
- **Replay diff visualization** — compare original and forked executions.
- **Trace search and filtering** — make large trace sets easier to navigate.
- **Failed-step visualization** — improve error inspection and navigation.
- **Deterministic replay tests** — expand the replay safety test matrix.
- **Timeline keyboard controls** — improve accessibility and navigation.

There are also larger integration tasks for CrewAI and OpenTelemetry.

If you want to work on an issue, comment on it first so effort is not duplicated. Pull requests should include tests and documentation where appropriate.

## Project structure

```
sdk/       Agent tracing SDK
backend/   FastAPI API + replay engine
frontend/  Next.js debugger UI
examples/  Sample execution traces and integrations
```

## Status

Early working implementation. The replay model and UI are intended as a foundation for deeper agent observability, deterministic tool replay, branching execution, and production hardening.

## Links

- **Live demo:** https://ai-time-travel-debugger.onrender.com
- **GitHub:** https://github.com/UjwalBagalkoti/ai-time-travel-debugger
- **API docs:** https://ai-time-travel-debugger-api.onrender.com/docs
