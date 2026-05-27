# Project: devdocs-agent

This repository contains an AI agent designed to help developers navigate and search through a collection of system design documentation.

## Architecture

- **Backend:** Python 3.12+ application using [pydantic-ai](https://github.com/pydantic/pydantic-ai).
- **AI Agent:** Defined in `backend/agent.py`. It uses the `gpt-4o` model.
- **Knowledge Base:** Located in `backend/docs/`. This directory contains various system design topics in Markdown format.
- **Tools:** The agent's capabilities are implemented in `backend/utils/tools.py` and exposed as agent tools.

## Development Workflow

### Prerequisites

- Python 3.12 or higher.
- [uv](https://github.com/astral-sh/uv) for dependency management.
- An OpenAI API key.

### Setup

1.  **Environment Variables:** Create a `.env` file in the root (or `backend/`) and add your `OPENAI_API_KEY`.
    ```env
    OPENAI_API_KEY=your_api_key_here
    ```
2.  **Virtual Environment & Dependencies:** Create and manage the virtual environment directly within the `backend/` directory.
    ```bash
    cd backend
    uv sync
    ```
    - **Note:** `uv` will automatically create a `.venv` inside `backend/`. Keeping the environment here ensures that tooling and dependency resolution stay aligned with the `pyproject.toml` location.

### Running the Agent

- The entry point for the application is `backend/main.py`.

## Coding Conventions

- **Type Hinting:** All new Python code should be strictly typed.
- **Tools:** Use `@agent.tool_plain` for tools that don't require agent context.
- **File Operations:** Prefer `pathlib` for all file and directory manipulations.
- **Documentation:** Maintain the Markdown files in `backend/docs/` as the primary knowledge source. Use descriptive filenames.

## Directory Structure

- `backend/`: Python backend code.
  - `agent.py`: Agent definition and tool registration.
  - `main.py`: Entry point.
  - `utils/tools.py`: Implementation of search and read functions.
  - `docs/`: Knowledge base of system design concepts.
- `frontend/`: (Currently empty) Placeholder for a future user interface.
