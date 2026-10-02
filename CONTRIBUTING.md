# Contributing

Thanks for contributing to AI Time-Travel Debugger.

This project is an open-source debugging and replay layer for AI agents. Contributions that make agent execution easier to inspect, reproduce, replay, or integrate with existing frameworks are especially welcome.

## Ways to contribute

- Add integrations for agent frameworks such as LangGraph, LangChain, CrewAI, AutoGen, or other agent runtimes.
- Improve deterministic tool replay and state isolation.
- Add tests for replay, branching, malformed traces, and failure cases.
- Improve the FastAPI backend or React Flow debugger UI.
- Improve the Python SDK and developer experience.
- Improve documentation, examples, and troubleshooting guides.
- Report reproducible bugs or propose focused feature improvements.

## Before opening an issue

Please search existing issues first.

For bug reports, include:

- What you expected to happen.
- What actually happened.
- Steps to reproduce.
- Relevant trace or a minimal reproduction, with secrets and private data removed.
- Python/Node/runtime versions when relevant.
- Logs or error messages when available.

For feature requests, explain:

- The developer problem you are trying to solve.
- Why the current behavior is insufficient.
- A concrete example of the desired workflow.
- Whether the proposal affects the SDK, backend, frontend, or an integration.

## Framework integrations

Framework integrations should ideally:

1. Capture meaningful agent/tool/LLM execution boundaries.
2. Preserve enough state to reproduce the execution.
3. Avoid re-running external side effects during replay by default.
4. Keep the integration optional so the core SDK remains lightweight.
5. Include a small example and automated tests.

When proposing an integration, please open an issue first if the design is substantial. Useful examples include:

- LangGraph connector
- LangChain integration
- CrewAI integration
- OpenAI tool/function-calling integration
- Anthropic tool-use integration

## Development

The repository contains:

- `sdk/` — Python tracing SDK
- `backend/` — FastAPI API and replay engine
- `frontend/` — Next.js + React Flow debugger
- `examples/` — example traces

For the local stack:

```bash
docker-compose up --build
```

Then open the local debugger at `http://localhost:3000` and the API docs at `http://localhost:8000/docs`.

Run backend tests with:

```bash
cd backend
pytest
```

## Pull requests

Please keep pull requests focused and explain:

- What changed.
- Why it changed.
- How it was tested.
- Any compatibility or migration considerations.

New framework integrations should include tests and documentation where practical.

## Security and privacy

Never commit API keys, credentials, private traces, customer data, or other secrets.

When sharing traces in issues or pull requests, remove sensitive prompts, tool arguments, identifiers, and outputs first.

## License

By contributing, you agree that your contributions are provided under the repository's MIT License.
