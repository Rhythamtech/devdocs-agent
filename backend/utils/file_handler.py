import re
import datetime
from pathlib import Path
from fastapi import HTTPException, status
from core.config import settings

ALLOWED_EXTENSIONS = {".md", ".txt"}

def get_user_upload_dir(username: str) -> Path:
    """Get user's upload directory absolute path, ensuring it is within the root."""
    backend_dir = Path(__file__).resolve().parent.parent
    root_uploads = (backend_dir / settings.UPLOADS_ROOT).resolve()
    
    # Sanitize username to prevent directory traversal
    safe_username = re.sub(r'[^a-zA-Z0-9_-]', '_', username.lower())
    user_dir = (root_uploads / safe_username).resolve()
    
    # Double check it remains within the root directory
    if not user_dir.is_relative_to(root_uploads):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid username storage path."
        )
    return user_dir

def sanitize_filename(filename: str) -> str:
    """Sanitize the filename to be safe for local filesystem."""
    # Extracted name and lowercased suffix
    path = Path(filename)
    suffix = path.suffix.lower()
    
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Only {', '.join(ALLOWED_EXTENSIONS)} are allowed."
        )
        
    stem = path.stem
    # Replace non-alphanumeric with underscores
    safe_stem = re.sub(r'[^a-zA-Z0-9_-]', '_', stem)
    # Avoid empty or dot-starting stems
    if not safe_stem or safe_stem.startswith('.'):
        safe_stem = "file_" + safe_stem
        
    return f"{safe_stem}{suffix}"

def validate_file_size(size_bytes: int) -> None:
    """Validate that the file size doesn't exceed the limit."""
    if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large. Maximum allowed size is {max_mb:.1f} MB."
        )

def save_upload(username: str, original_filename: str, content: bytes) -> str:
    """Save an uploaded file content to the user's upload directory."""
    validate_file_size(len(content))
    safe_filename = sanitize_filename(original_filename)
    
    user_dir = get_user_upload_dir(username)
    user_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = user_dir / safe_filename
    file_path.write_bytes(content)
    
    return safe_filename

def delete_upload(username: str, filename: str) -> None:
    """Delete a user's uploaded file."""
    user_dir = get_user_upload_dir(username)
    
    # Path traversal validation
    safe_filename = Path(filename).name
    file_path = (user_dir / safe_filename).resolve()
    
    if not file_path.is_relative_to(user_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access denied."
        )
        
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found."
        )
        
    file_path.unlink()

def list_uploads(username: str) -> list[dict]:
    """List all uploaded files with their metadata for a user."""
    user_dir = get_user_upload_dir(username)
    
    if not user_dir.exists() or not user_dir.is_dir():
        return []
        
    docs = []
    # Only glob for allowed extensions
    for ext in ALLOWED_EXTENSIONS:
        for file in user_dir.glob(f"*{ext}"):
            if file.is_file():
                stat = file.stat()
                mtime = datetime.datetime.fromtimestamp(stat.st_mtime, datetime.timezone.utc)
                docs.append({
                    "filename": file.name,
                    "size_bytes": stat.st_size,
                    "uploaded_at": mtime.isoformat()
                })
                
    # Sort docs by upload time descending
    docs.sort(key=lambda d: d["uploaded_at"], reverse=True)
    return docs

def initialize_user_docs(username: str) -> None:
    """Initialize a user's uploads directory with the default devdocs.md file."""
    user_dir = get_user_upload_dir(username)
    user_dir.mkdir(parents=True, exist_ok=True)
    
    devdocs_path = user_dir / "devdocs.md"
    if not devdocs_path.exists():
        content = """# DevDocs Agent

DevDocs Agent is an AI assistant designed to help developers navigate and search through system design documentation.

## What It Is

DevDocs Agent is a specialized system design documentation assistant. It uses an AI agent to search, read, and explain system design concepts based on the documents uploaded by the user.

## Why This Exists

In modern software development, documentation is often scattered across different repositories, wikis, and design documents. DevDocs Agent solves this by providing a unified, context-aware AI interface. It allows users to upload system design documents and search across them securely. Each user has an isolated workspace, ensuring privacy and preventing information leakage.

## Architecture

The system is split into three main parts:

1. **Frontend UI (NovaFlow):** Built with Next.js, React, TailwindCSS, and shadcn/ui components. It uses a modern dark theme and provides a clean interface for chatting with the agent, uploading documentation, and managing files.
2. **Backend Service:** A Python 3.12+ FastAPI application that handles user authentication, session state, files, and coordinates requests with the AI Agent.
3. **AI Agent (Agno):** Built using the Agno framework (formerly Phidata). It uses local tools to search (`grep`, `list_all_docs`) and read (`read_doc`, `read_slice_doc`) documents in the user's isolated storage.

## System Design

### 1. Isolated File Storage
User-uploaded documentation is saved in user-specific subdirectories under `backend/docs/uploads/<username>/`. The system uses `contextvars.ContextVar` to set the active user directory on request threads. This isolates the agent's tools to the specific user's folder, preventing unauthorized file access.

### 2. Database Schema
MongoDB is used to store user registration, user session history, refresh tokens, and Agno's internal message log collections:
* **users:** Stores user registration details with hashed passwords (Argon2id).
* **sessions:** Manages the mapping of user IDs to agent session IDs, enabling user ownership of sessions.
* **refresh_tokens:** Stores hashed refresh tokens for JWT session management.
* **audit_logs:** Tracks metrics like prompt length, model used, latency, and status for request auditing.

### 3. Agent Tool Flow
When a user asks a question, the agent:
1. Translates the prompt to coordinate tool calls.
2. Queries the user's isolated documents using tools like `grep` or `list_all_docs`.
3. Reads contents using `read_doc` or `read_slice_doc`.
4. Synthesizes the information into a direct answer with source citations, complying with the constraint of not returning raw content snippets without explanation.
"""
        devdocs_path.write_text(content.strip(), encoding="utf-8")

