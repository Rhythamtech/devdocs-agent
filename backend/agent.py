import os
import httpx
from openai import OpenAI
from typing import Any, Iterator
from dotenv import load_dotenv
import agentops
from utils.handler import SyncKeymeshTransport
from keymesh import SyncKeyPool, SchedulerStrategy
from agno.agent import Agent, RunEvent
from agno.models.openai.like import OpenAILike
from agno.db.mongo import MongoDb
from utils.tools import list_all_docs, grep, read_slice_doc, read_doc
from schema import AgentResponse, ToolResponse
from os import getenv
from core.config import settings

# Get your Supabase project and password

# Load .env from the project root (one level up from backend/)
load_dotenv()



class DocumentationAgent:
    def __init__(self) -> None:
       
        db_url = settings.MONGO_DB_URL

        db = MongoDb(db_url=db_url)
        
        api_keys_str = os.getenv("OPENAI_API_KEYS")
        agentops.init()

            
        if not api_keys_str:
            raise ValueError("OPENAI_API_KEYS environment variable is not set.")
            
        api_keys = [k.strip() for k in str(api_keys_str).split(",")]
        base_url = settings.OPENAI_BASE_URL
        model = settings.OPENAI_MODEL
        
        self._pool = SyncKeyPool(keys=api_keys, strategy=SchedulerStrategy.ROUND_ROBIN)
        
        transport = SyncKeymeshTransport(httpx.HTTPTransport(), self._pool)
        http_client = httpx.Client(transport=transport)
        
        openai_client = OpenAI(
            api_key="dummy",  # Replaced dynamically by transport
            base_url=base_url,
            http_client=http_client
        )

        model_provider = OpenAILike(
            id=model,
            client=openai_client,
        )
        
        instructions = """
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

        self.agent = Agent(
            model=model_provider,
            instructions=instructions,
            tools=[list_all_docs, grep, read_slice_doc, read_doc],
            tool_choice="auto",
            compress_tool_results=True,
            tool_call_limit=4,
            max_tool_calls_from_history = 0,
            db=db,
            read_chat_history=True,  # Agent gets a get_chat_history() tool

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

    def ask(self, prompt: str, session_id: str | None = None) -> AgentResponse:
        response = self.agent.run(prompt, session_id=session_id)
        return self.parse_agent_output(response)

    def stream(self, prompt: str, session_id: str | None = None) -> Iterator[str]:
        response = self.agent.run(prompt, session_id=session_id, stream=True, stream_events=True)

        for event in response:
            if event.event == RunEvent.tool_call_started and event.tool:
                yield f"data: Tool Call: {event.tool.tool_name}({event.tool.tool_args})\n\n"
            elif event.event == RunEvent.run_content and event.content:
                yield f"data: {event.content}\n\n"

        yield "data: [DONE]\n\n"

    def get_chat_history(self, session_id: str) -> list[dict[str, Any]]:
        try:
            history = self.agent.get_chat_history(session_id=session_id)
            return [m.to_dict() for m in history]
        except Exception as e:
            if "Session not found" in str(e):
                return []
            raise e
        
        
if __name__ == "__main__":
    agent = DocumentationAgent()
    prompt = "What caching strategies are available in Redis?"
    print(f"Question: {prompt}\n")
    # response = agent.stream(prompt, session_id="test-session")
    # for chunk in response:
    #     print(chunk, end="", flush=True)
    response = agent.ask(prompt, session_id="test-session")
    print(f"Answer: {response.content}\n")