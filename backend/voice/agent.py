"""LiveKit voice worker for DevDocs Agent.

The worker shares the FastAPI uploads directory and reuses the exact same
document tools (`list_all_docs`, `grep`, `read_doc`, `read_slice_doc`).

Run it from the backend directory:

    uv run python -m voice.agent dev      # development (auto-reload)
    uv run python -m voice.agent start    # production
"""

from __future__ import annotations

import json
import logging
import os

from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    RunContext,
    TurnHandlingOptions,
    function_tool,
    inference,
)
from livekit.plugins import deepgram

from core.config import settings
from utils.tools import grep, list_all_docs, read_doc, read_slice_doc, use_user_docs

logger = logging.getLogger("devdocs.voice")

MAX_TOOL_CHARS = 6000


def _export_sdk_env() -> None:
    """Bridge pydantic settings into the environment the LiveKit SDK reads.

    Locally the values come from the repository .env file, which pydantic reads
    directly without exporting it to os.environ. The LiveKit worker and CLI
    read LIVEKIT_* from the process environment.
    """
    values = {
        "LIVEKIT_URL": settings.LIVEKIT_URL,
        "LIVEKIT_API_KEY": settings.LIVEKIT_API_KEY,
        "LIVEKIT_API_SECRET": settings.LIVEKIT_API_SECRET,
        "DEEPGRAM_API_KEY": settings.DEEPGRAM_API_KEY,
    }
    for key, value in values.items():
        if value:
            # Settings already resolved environment > .env, so this is the
            # effective value; assign rather than setdefault so a stale empty
            # variable cannot mask the .env value.
            os.environ[key] = value


_export_sdk_env()

INSTRUCTIONS = """
You are the DevDocs voice assistant. You answer spoken questions about the
documentation the signed-in user has uploaded.

Rules:
- Only answer from the user's uploaded documents. Search or read them with your
  tools before answering. Never rely on general knowledge for their content.
- If the documents do not contain the answer, say you could not find it in the
  uploaded documents. Never invent an answer.
- Keep every answer to one to three short spoken sentences. Plain speech only:
  no markdown, bullet points, code fences, emojis, or symbols.
- Name the source file you used, for example "from architecture dot markdown".
- Read identifiers and acronyms naturally, and expand them when helpful.
- If the question is unrelated to the user's documents, politely redirect them.
- Always speak English.
""".strip()

GREETING = (
    "Greet the user in one short sentence and ask what they would like to know "
    "about their uploaded documents."
)


def _metadata_username(metadata: str | None) -> str | None:
    """Read the username the FastAPI token endpoint dispatched with the job."""
    if not metadata:
        return None

    try:
        payload = json.loads(metadata)
    except json.JSONDecodeError:
        logger.warning("Voice job metadata is not valid JSON: %r", metadata)
        return None

    username = payload.get("username") if isinstance(payload, dict) else None
    if isinstance(username, str) and username.strip():
        return username.strip()
    return None


def _first_participant_identity(ctx: JobContext) -> str | None:
    for participant in ctx.room.remote_participants.values():
        if participant.identity:
            return participant.identity
    return None


def _keyterms() -> list[str]:
    return [term.strip() for term in settings.VOICE_KEYTERMS.split(",") if term.strip()]


def _voice_configured() -> bool:
    return all(
        (
            settings.LIVEKIT_URL,
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
            settings.DEEPGRAM_API_KEY,
        )
    )


def _clip(text: str) -> str:
    if len(text) <= MAX_TOOL_CHARS:
        return text
    return f"{text[:MAX_TOOL_CHARS]}\n\n[truncated — read a smaller slice for more]"


class DocsAgent(Agent):
    """Voice agent grounded in one user's uploaded documentation."""

    def __init__(self, username: str) -> None:
        self._username = username
        super().__init__(instructions=INSTRUCTIONS)

    def _call_tool(self, tool, *args):
        # The worker process handles one user per room, but the ContextVar keeps
        # the shared document tools scoped the same way the FastAPI path does.
        with use_user_docs(self._username):
            return tool(*args)

    @function_tool()
    async def list_docs(self, context: RunContext) -> str:
        """List every document the user has uploaded.

        Use this when you are not sure which files exist.
        """
        files = self._call_tool(list_all_docs)
        if not files:
            return "The user has not uploaded any documents yet."
        return _clip("\n".join(str(path) for path in files))

    @function_tool()
    async def search_docs(self, context: RunContext, query: str) -> str:
        """Search the user's uploaded documents for a word or phrase.

        Args:
            query: The word or regular expression to search for.
        """
        results = self._call_tool(grep, query, 8)
        if not results:
            return f"No matches found for {query!r} in the uploaded documents."
        return _clip("\n".join(results))

    @function_tool()
    async def read_document(self, context: RunContext, path: str) -> str:
        """Read a document in full.

        Args:
            path: File path relative to the user's upload directory, for example
                "architecture.md".
        """
        content = self._call_tool(read_doc, path)
        if not content:
            return f"The document {path!r} is empty."
        return _clip(content)

    @function_tool()
    async def read_document_slice(
        self,
        context: RunContext,
        path: str,
        start_line: int,
        end_line: int,
    ) -> str:
        """Read part of a document when it is too long to read in full.

        Args:
            path: File path relative to the user's upload directory.
            start_line: First line to read, starting at 1.
            end_line: Last line to read, inclusive.
        """
        content = self._call_tool(read_slice_doc, path, start_line, end_line)
        if not content:
            return "That line range is empty."
        return _clip(content)


# One pre-warmed job process is plenty for a single-room documentation app.
server = AgentServer(num_idle_processes=1)


@server.rtc_session(agent_name=settings.VOICE_AGENT_NAME)
async def devdocs_voice(ctx: JobContext) -> None:
    if not settings.DEEPGRAM_API_KEY:
        logger.error(
            "DEEPGRAM_API_KEY is not set — the voice agent cannot start. "
            "Add it to the repository .env file."
        )
        return

    username = _metadata_username(ctx.job.metadata)
    if not username:
        # Explicit dispatch should always carry metadata. Fall back to the
        # participant identity so a manually started room still works.
        await ctx.connect()
        await ctx.wait_for_participant()
        username = _first_participant_identity(ctx)

    if not username:
        logger.error("Could not resolve a username for this voice room.")
        return

    logger.info("Starting DevDocs voice session for user %s", username)

    session = AgentSession(
        stt=deepgram.STTv2(
            model=settings.VOICE_STT_MODEL,
            api_key=settings.DEEPGRAM_API_KEY,
            keyterm=_keyterms(),
            audio_chunk_duration_ms=80,
        ),
        llm=inference.LLM(model=settings.VOICE_LLM_MODEL),
        tts=deepgram.TTS(
            model=settings.VOICE_TTS_MODEL,
            api_key=settings.DEEPGRAM_API_KEY,
        ),
        turn_handling=TurnHandlingOptions(turn_detection="stt"),
    )

    await session.start(room=ctx.room, agent=DocsAgent(username))
    await session.generate_reply(instructions=GREETING)


if __name__ == "__main__":
    if not _voice_configured():
        logger.warning(
            "Voice is not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, "
            "LIVEKIT_API_SECRET, and DEEPGRAM_API_KEY to start the worker."
        )
        raise SystemExit(0)

    agents.cli.run_app(server)
