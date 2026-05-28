import json
from typing import Any, Iterator, Union, Optional
from agno.agent import RunOutput, RunOutputEvent, RunEvent
from pydantic import BaseModel

def format_agent_output(
    run_output: Union[RunOutput, Iterator[RunOutputEvent]], 
    stream: bool = False
) -> Iterator[str]:
    """
    Standardizes the agent's output into a consistent JSON format.
    
    Format: {"event": "event_type", "data": payload}
    """
    if not stream:
        if isinstance(run_output, RunOutput):
            # Final response
            content = run_output.content
            if isinstance(content, BaseModel):
                data = content.model_dump()
            else:
                data = content
            
            yield json.dumps({
                "event": "final_response",
                "data": data
            })
        return

    # Streaming mode
    for event in run_output:
        payload = None
        event_type = "unknown"

        if event.event == RunEvent.run_started:
            event_type = "run_started"
            payload = event.content
        elif event.event == RunEvent.run_content:
            event_type = "content"
            payload = event.content
        elif event.event == RunEvent.tool_call_started:
            event_type = "tool_call"
            payload = event.content
        elif event.event == RunEvent.tool_call_completed:
            event_type = "tool_result"
            payload = event.content
        elif event.event == RunEvent.run_completed:
            event_type = "run_completed"
            # In streaming mode, the final content might be in the last event
            if isinstance(event.content, BaseModel):
                payload = event.content.model_dump()
            else:
                payload = event.content
        else:
            event_type = str(event.event)
            payload = event.content

        yield json.dumps({
            "event": event_type,
            "data": payload
        })
