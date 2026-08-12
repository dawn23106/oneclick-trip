# OneClick Travel Agent

FastAPI and LangGraph service for the OneClick Trip application. It handles
travel intent recognition, itinerary planning and modification, read-only
travel queries, booking drafts, conversation state, and knowledge retrieval.

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
