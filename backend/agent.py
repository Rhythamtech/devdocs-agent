import os
import json
from typing import Any
from dotenv import load_dotenv
from agno.agent import Agent, RunOutput
from agno.models.openai.like import OpenAILike
from utils.tools import list_all_docs, grep, read_slice_doc, read_doc
from schema import AgentResponse, ToolResponse

load_dotenv()  # Load environment variables from .env file

# Initialize the model (requires OPENAI_API_KEY environment variable)


api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
model = os.getenv("OPENAI_MODEL", "gpt-4o")

model_provider = OpenAILike(api_key=api_key, base_url=base_url, id=model)



if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")

instructions = """
You are a documentation assistant.
Do not answer before you have checked the docs.
If the docs do not contain the answer, say you don't know.
Also citation is important, so always include the source of your information in the answer.
"""


agent = Agent(model=model_provider,
               instructions= instructions,
               tools=[list_all_docs, grep, read_slice_doc, read_doc],
               compress_tool_results = True,
               tool_choice = "auto",
               tool_call_limit = 4)

def parse_agent_output(output: Any) -> AgentResponse:
    """Parses RunOutput or RunOutputEvent into AgentResponse schema."""
    tool_resp = None
    
    tools = getattr(output, "tools", None)
    tool = getattr(output, "tool", None)
    
    if tools:
        last_tool = tools[-1]
        tool_resp = ToolResponse(
            content=str(last_tool.result) if last_tool.result is not None else "",
            name=last_tool.tool_name or "unknown",
            args=last_tool.tool_args or {}
        )
    elif tool:
        tool_resp = ToolResponse(
            content=str(tool.result) if tool.result is not None else "",
            name=tool.tool_name or "unknown",
            args=tool.tool_args or {}
        )
    
    content = getattr(output, "content", "")
    return AgentResponse(
        content=str(content) if content is not None else "",
        tool_response=tool_resp
    )


if __name__ == "__main__":
    prompt = "What caching strategies are available in Redis?"

    print(f"Question: {prompt}\n")
    response = agent.run(prompt, stream=True, stream_events=True)
    for output in response:
        parsed = parse_agent_output(output)
        if parsed.tool_response:
            print(f"Tool Call: {parsed.tool_response.name}({parsed.tool_response.args})")
            # print(f"Tool Result: {parsed.tool_response.content[:100]}...")
        if parsed.content:
            print(parsed.content, end="", flush=True)
    print("\n")

    
    response = agent.run(prompt)
    output = parse_agent_output(response)
    print(output)


