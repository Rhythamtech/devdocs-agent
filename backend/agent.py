import json
import os
from typing import Any, Iterator

import agentops
from agno.agent import Agent, RunEvent
from agno.db.postgres import PostgresDb
from agno.models.openai.like import OpenAILike
from agno.session import SessionSummaryManager
from core.config import settings
from core.database import AGNO_DB_SCHEMA, AGNO_SESSIONS_TABLE
from dotenv import load_dotenv
from keymesh import SchedulerStrategy, OpenAIHandler
from openai import OpenAI
from schema import AgentResponse, ToolResponse
from utils.tools import grep, list_all_docs, read_doc, read_slice_doc


from core.logger import logger

SUMMARY_MODEL_ID = "meta-llama/llama-4-scout-17b-16e-instruct"
SUMMARY_REQUEST_MESSAGE = (
    "Summarize the following conversation between a user and an "
    "assistant reduce it by 36%."
    "Focus on key details, questions asked, and information provided."
    " Keep it concise but informative."
)

AGENT_INSTRUCTIONS = """
You are a documentation assistant.
Answer questions using the documentation and provide a concise explanation. Do NOT return:

* file contents
* line-by-line matches
* search results
* document snippets without explanation

Instead, synthesize the information into a direct answer and then cite the source documents.

If the answer is not documented, respond only:
"I don't know based on the available documentation."
"""

AGENT_TOOLS = [list_all_docs, grep, read_slice_doc, read_doc]


def _sqlalchemy_url(url: str) -> str:
    """Point SQLAlchemy at psycopg v3 instead of the psycopg2 default."""
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    return url


# Load .env from the project root (one level up from backend/)
load_dotenv()


def _patch_agentops_otel_compat() -> None:
    """Keep AgentOps telemetry working with OpenTelemetry 1.45.

    livekit-agents requires OpenTelemetry >= 1.45, which moved the OTLP HTTP
    exporter's session headers onto an internal client. AgentOps 0.4.21 still
    reads the removed ``_headers`` and ``_session`` attributes when injecting
    its JWT, so expose the client's header mapping under the old names.
    """
    try:
        from importlib.metadata import version

        from agentops.sdk.exporters import AuthenticatedOTLPExporter
    except Exception:
        return

    try:
        exporter_version = version("opentelemetry-exporter-otlp-proto-http")
        major, minor = (int(part) for part in exporter_version.split(".")[:2])
    except Exception:
        return
    if (major, minor) < (1, 45):
        return

    class _SessionProxy:
        def __init__(self, client) -> None:
            self._client = client

        @property
        def headers(self):
            return self._client._headers

    if not isinstance(getattr(AuthenticatedOTLPExporter, "_headers", None), property):
        AuthenticatedOTLPExporter._headers = property(
            lambda self: self._client._headers
        )
    if not isinstance(getattr(AuthenticatedOTLPExporter, "_session", None), property):
        AuthenticatedOTLPExporter._session = property(
            lambda self: _SessionProxy(self._client)
        )


class DocumentationAgent:
    def __init__(self) -> None:
        _patch_agentops_otel_compat()
        agentops.init()

        openai_client = self._build_openai_client()
        model_provider = self._build_model_provider(openai_client, settings.OPENAI_MODEL)
        session_manager = self._build_session_manager(openai_client)
        self.db = PostgresDb(
            db_url=_sqlalchemy_url(settings.POSTGRES_URL),
            db_schema=AGNO_DB_SCHEMA,
            session_table=AGNO_SESSIONS_TABLE,
        )

        try:
            self.agent = Agent(
                model=model_provider,
                instructions=AGENT_INSTRUCTIONS,
                tools=AGENT_TOOLS,
                tool_choice="auto",
                compress_tool_results=True,
                tool_call_limit=4,
                enable_session_summaries=True,
                session_summary_manager=session_manager,
                max_tool_calls_from_history=0,
                db=self.db,
                read_chat_history=True,  # Agent gets a get_chat_history() tool
            )
        except Exception:
            self.db.close()
            raise

    def close(self) -> None:
        self.db.close()

    def _build_openai_client(self) -> OpenAI:
        api_keys = self._load_api_keys()
        openai_handler = OpenAIHandler(keys=api_keys, strategy=SchedulerStrategy.ROUND_ROBIN)

        return OpenAI(
            api_key="dummy",  # Replaced dynamically by transport
            base_url=settings.OPENAI_BASE_URL,
            http_client=openai_handler,
        )

    def _load_api_keys(self) -> list[str]:
        api_keys_str = os.getenv("OPENAI_API_KEYS")

        if not api_keys_str:
            raise ValueError("OPENAI_API_KEYS environment variable is not set.")

        return [key.strip() for key in str(api_keys_str).split(",")]

    def _build_model_provider(self, openai_client: OpenAI, model_id: str) -> OpenAILike:
        return OpenAILike(
            id=model_id,
            client=openai_client,
        )

    def _build_session_manager(self, openai_client: OpenAI) -> SessionSummaryManager:
        summary_model_provider = self._build_model_provider(
            openai_client,
            SUMMARY_MODEL_ID,
        )

        return SessionSummaryManager(
            model=summary_model_provider,
            summary_request_message=SUMMARY_REQUEST_MESSAGE,
            conversation_limit=4,
        )

    def parse_agent_output(self, output: Any) -> AgentResponse:
        tool_resp = None

        tools = getattr(output, "tools", None)
        tool = getattr(output, "tool", None)

        if tools:
            last_tool = tools[-1]
            tool_resp = ToolResponse(
                content=str(last_tool.result) if last_tool.result is not None else "",
                name=last_tool.tool_name or "unknown",
                args=last_tool.tool_args or {},
            )
        elif tool:
            tool_resp = ToolResponse(
                content=str(tool.result) if tool.result is not None else "",
                name=tool.tool_name or "unknown",
                args=tool.tool_args or {},
            )

        content = getattr(output, "content", "")
        return AgentResponse(
            content=str(content) if content is not None else "",
            tool_response=tool_resp,
        )

    def ask(
        self,
        prompt: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> AgentResponse:
        response = self.agent.run(prompt, session_id=session_id, user_id=user_id)
        return self.parse_agent_output(response)

    def stream(
        self,
        prompt: str,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> Iterator[str]:
        response = self.agent.run(
            prompt,
            session_id=session_id,
            user_id=user_id,
            stream=True,
            stream_events=True,
        )

        for event in response:
            if event.event == RunEvent.tool_call_started and event.tool:
                yield f"data: Tool Call: {event.tool.tool_name}({event.tool.tool_args})\n\n"
            elif event.event == RunEvent.run_content and event.content:
                yield f"data: {json.dumps(event.content)}\n\n"

        yield "data: [DONE]\n\n"

    def get_chat_history(self, session_id: str) -> list[dict[str, Any]]:
        try:
            history = self.agent.get_chat_history(session_id=session_id)
            return [m.to_dict() for m in history]
        except Exception as e:
            if "Session not found" in str(e):
                return []
            raise e
