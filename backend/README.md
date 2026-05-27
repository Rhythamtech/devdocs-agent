# DevDocs Agent - Backend

The backend for **DevDocs Agent**, an AI-powered assistant designed to help developers navigate and search through system design documentation.

## Features

- **AI-Powered Search:** Leverages `pydantic-ai` and LLMs to understand and answer questions based on local documentation.
- **Documentation Tools:** Custom tools for listing, searching (regex/grep), and reading Markdown documents.
- **Streaming Support:** Built-in support for streaming agent steps and tool executions.
- **Local Knowledge Base:** Uses a collection of system design Markdown files as its primary source of truth.

## Tech Stack

- **Python 3.12+**
- **[Pydantic AI](https://github.com/pydantic/pydantic-ai):** For building the agent and tool definitions.
- **[uv](https://github.com/astral-sh/uv):** For fast and reliable dependency management.
- **Groq/OpenAI:** Supports various LLM providers (currently configured for Groq via `pydantic-ai`).

## Project Structure

```text
backend/
├── docs/               # Knowledge base (Markdown files)
├── utils/
│   ├── streaming.py    # Utilities for formatting and streaming output
│   └── tools.py        # Implementation of documentation interaction tools
├── agent.py            # Main agent definition and tool registration
├── main.py             # Entry point (currently a placeholder)
├── schema.py           # Pydantic models for data validation
└── pyproject.toml      # Project dependencies and configuration
```

## Setup & Installation

### Prerequisites

- Python 3.12 or higher.
- [uv](https://github.com/astral-sh/uv) installed.

### 1. Environment Configuration

Create a `.env` file in the `backend/` directory (or use the one in the root) with the following variables:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional
OPENAI_MODEL=gpt-4o                        # Or your preferred model
```

*Note: While the code uses `GroqModel`, it currently relies on `OPENAI_API_KEY` for authentication as per the standard environment configuration.*

### 2. Install Dependencies

Use `uv` to sync dependencies and create a virtual environment:

```bash
cd backend
uv sync
```

## Usage

You can run the agent directly from `agent.py` to see it in action with example queries:

```bash
python agent.py
```

### Example

The agent can handle queries like:
- "How to start system design?"
- "List all documents related to Kafka."
- "What is the difference between Optimistic and Pessimistic locking?"

## Documentation Tools

The agent has access to several tools defined in `utils/tools.py`:

- `list_docs(pattern)`: Lists all documents in the `docs/` directory matching a glob pattern.
- `search_docs(pattern, max_results)`: Performs a regex search across all documentation files.
- `read_document(path)`: Reads the full content of a specific document.
- `read_document_slice(path, start_line, end_line)`: Reads a specific range of lines from a document.

## Coding Conventions

- **Type Hinting:** Strictly typed Python code.
- **Path Management:** Uses `pathlib` for all file operations.
- **Tool Registration:** Uses `@agent.tool_plain` for standalone tools.
