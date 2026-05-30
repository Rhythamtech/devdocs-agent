import os
import httpx
from openai import OpenAI
from typing import Any, Iterator
from dotenv import load_dotenv
from utils.handler import SyncKeymeshTransport
from keymesh import SyncKeyPool, SchedulerStrategy
from agno.agent import Agent, RunEvent
from agno.models.openai.like import OpenAILike
from utils.tools import list_all_docs, grep, read_slice_doc, read_doc
from schema import AgentResponse, ToolResponse

from pathlib import Path

# Load .env from the project root (one level up from backend/)
load_dotenv()



class DocumentationAgent:
    def __init__(self) -> None:
        api_keys_str = os.getenv("OPENAI_API_KEYS")
        
        if not api_keys_str:
            raise ValueError("OPENAI_API_KEYS environment variable is not set.")
            
        api_keys = [k.strip() for k in str(api_keys_str).split(",")]
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")

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
            Do not answer before you have checked the docs.
            If the docs do not contain the answer, say you don't know.
            Also citation is important, so always include the source of your information in the answer.
            """

        self.agent = Agent(
            model=model_provider,
            instructions=instructions,
            tools=[list_all_docs, grep, read_slice_doc, read_doc],
            tool_choice="auto",
            tool_call_limit=4,
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

    def ask(self, prompt: str) -> AgentResponse:
        response = self.agent.run(prompt)
        return self.parse_agent_output(response)

    def stream(self, prompt: str) -> Iterator[str]:
        response = self.agent.run(prompt, stream=True, stream_events=True)

        for event in response:
            if event.event == RunEvent.tool_call_started and event.tool:
                yield f"data: Tool Call: {event.tool.tool_name}({event.tool.tool_args})\n\n"
            elif event.event == RunEvent.run_content and event.content:
                yield f"data: {event.content}\n\n"

        yield "data: [DONE]\n\n"
        
        
if __name__ == "__main__":
    agent = DocumentationAgent()
    prompt = "What caching strategies are available in Redis?"
    print(f"Question: {prompt}\n")
    response = agent.stream(prompt)
    for chunk in response:
        print(chunk, end="", flush=True)
