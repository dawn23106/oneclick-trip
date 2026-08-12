# OneClick Travel Agent

FastAPI and LangGraph service for the OneClick Trip application. It handles
travel intent recognition, itinerary planning and modification, read-only
travel queries, booking drafts, conversation state, and knowledge retrieval.

## Architecture

The service uses an explicit LangGraph `StateGraph` as its workflow backbone.
The root graph restores conversation state and user memory, recognizes intent,
and uses a code-controlled Supervisor to route work into query, planning,
modification, and booking subgraphs. This keeps deterministic business rules
separate from model-driven reasoning instead of delegating the entire workflow
to a generic ReAct loop.

- The planning subgraph runs research, candidate selection, hard validation,
  Agent review, and code-repair/replanning loops before a plan is persisted.
- Redis Checkpoint persists the shared `TravelState`; compiled child graphs
  inherit the parent graph's state and persistence context.
- The booking subgraph uses `interrupt` and `Command(resume=...)` for explicit
  human confirmation before a draft is confirmed or cancelled.

## Local development

Requires Python 3.11 or newer.

```bash
uv sync --dev
uv run pytest
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Copy `.env.example` to `.env` for local-only configuration. Never commit the
resulting `.env` file or production credentials.

## Production

The repository-level `compose.production.yml` builds this service and connects
it to the Java backend, Redis, and Chroma. Runtime secrets are supplied through
an untracked production environment file based on `production.env.example`.
