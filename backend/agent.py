import os
import asyncio
from dotenv import load_dotenv
from typing import Optional
from pydantic_ai import Agent
from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent
from utils.streaming import format_tool_result
from pydantic_ai.models.groq import GroqModel
from utils.tools import list_all_docs, grep, read_slice_doc, read_doc

load_dotenv()  # Load environment variables from .env file

# Initialize the model (requires OPENAI_API_KEY environment variable)

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
model_name = os.getenv("OPENAI_MODEL", "gpt-4")

if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")

model = GroqModel(model_name)

agent = Agent(model=model,
               instructions= ("Use the provided tools to interact with the documentation."
                            "Always use the tools when you need to access or search the documents."
                            "If you don't know the answer, say you don't know instead of making up an answer."),)


@agent.tool_plain(retries=3)
def list_docs(pattern: str = "*.md") -> list[str]:
    """List all documents in the docs directory."""
    return [str(p) for p in list_all_docs(pattern)]

@agent.tool_plain(retries=3)
def search_docs(pattern: str, max_results: int = 5) -> list[str]:
    """Search for a regex pattern in all markdown files."""
    return grep(pattern, max_results)

@agent.tool_plain(retries=3)
def read_document(path: str) -> str:
    """Read the full content of a document by its relative path."""
    return read_doc(path)

@agent.tool_plain(retries=3)
def read_document_slice(path: str, start_line: int, end_line: Optional[int] = None) -> str:
    """Read a specific slice of a document by line numbers."""
    return read_slice_doc(path, start_line, end_line)



async def run_with_visible_steps(question: str, debug: bool = False) -> str:
    print(f"\nQ: {question}\n")
    print("--- agent steps ---")
    tool_names: dict[str, str] = {}

    async with agent.iter(question) as run:
        async for node in run:
            if Agent.is_call_tools_node(node):
                async with node.stream(run.ctx) as tool_stream:
                    async for event in tool_stream:
                        if isinstance(event, FunctionToolCallEvent):
                            tool_names[event.tool_call_id] = event.part.tool_name
                            print(
                                f"-> {event.part.tool_name}({event.part.args_as_json_str()})"
                            )
                        elif debug and isinstance(event, FunctionToolResultEvent):
                            print(format_tool_result(event, tool_names))

    print("--- done ---\n")
    return run.result.output

if __name__ == "__main__":    # Example usage
    response = asyncio.run(
        run_with_visible_steps(
            "What you know about split brain problem, majority voting, fecning token, zookerper?",
            debug=False,
        )
    )

    print(f"Agent response:01 {"-"*10}" )
    print(response)


