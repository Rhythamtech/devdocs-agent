# DevDocs Agent - Backend

Backend service for **DevDocs Agent**, an AI assistant that answers questions using the local Markdown documentation corpus under `backend/docs/`.

## What it does

- Exposes a FastAPI service with `/ask`, `/ask/stream`, `/chats`, and `/health`
- Uses an Agno agent with OpenAI-compatible model access
- Searches and reads local documentation files through controlled tools
- Stores chat history in MongoDB through Agno's `MongoDb` backend

## Tech Stack

- Python 3.12+
- FastAPI
- Agno
- OpenAI-compatible chat completions API
- MongoDB
- `uv` for dependency management

## Project Structure

```text
backend/
├── docs/               # Knowledge base in Markdown
├── utils/
│   ├── handler.py      # Custom HTTP transport for API key rotation
│   └── tools.py        # Document listing/search/read tools
├── agent.py            # Agent initialization and chat history helpers
├── main.py             # FastAPI application and routes
├── schema.py           # Pydantic request/response models
└── pyproject.toml      # Dependencies
```

## Configuration

Create a `.env` file at the repository root or in `backend/` with:

```env
OPENAI_API_KEYS=key1,key2,key3
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

Required runtime dependency:

```env
MONGODB_URL=mongodb://localhost:27017
```

Notes:

- `OPENAI_API_KEYS` is a comma-separated list. Requests are rotated across keys with `keymesh`.
- `OPENAI_BASE_URL` should point to an OpenAI-compatible endpoint. The default is the public OpenAI API.
- `OPENAI_MODEL` selects the model name passed to the provider.
- The current code uses a local MongoDB instance for chat persistence.

## Install

```bash
cd backend
uv sync
```

## Run

```bash
cd backend
uv run uvicorn main:app --reload
```

API docs are available at:

- `GET /docs`
- `GET /redoc`

## Endpoints

### `GET /health`
Returns basic service health.

### `POST /ask`
Body:

```json
{
  "prompt": "What caching strategies are available in Redis?",
  "session_id": "optional-session-id"
}
```

Returns a structured response with the assistant answer and, when available, the last tool invocation.

### `POST /ask/stream`
Server-sent event stream for incremental output.

### `GET /chats?session_id=...`
Returns stored chat history for a session.

## Tools

The agent can use four local tools:

- `list_all_docs(pattern)` - list Markdown files under `backend/docs/`
- `grep(pattern, max_results)` - regex search across Markdown files
- `read_slice_doc(path, start_line, end_line)` - read a line range from a document
- `read_doc(path)` - read a full document

## Important Runtime Constraints

- Prompt length is capped at 10,000 characters in `main.py`
- CORS is currently wide open in code and should be narrowed before public deployment
- Chat history depends on MongoDB being available
- The agent is instantiated at import time in the current codebase

## Production Checklist

- Replace hardcoded MongoDB connection values with configuration
- Add authentication and rate limiting
- Restrict CORS to allowed origins
- Add request logging, metrics, and tracing
- Add tests for routes, agent init, and tool behavior
- Add a Dockerfile and deployment config

