import os
from agent import DocumentationAgent
from agno.agent import RunEvent

def test_stream():
    agent = DocumentationAgent()
    prompt = "If i have to renew 1000 accounts subscriptions, what is the best approach?"
    print(f"Question: {prompt}\n")
    
    # We'll call the internal agent.run directly to see all events
    response = agent.agent.run(prompt, stream=True, stream_events=True)
    
    for event in response:
        print(f"Event: {event.event}")
        if event.event == RunEvent.tool_call_started:
            print(f"  Tool: {event.tool.tool_name if event.tool else 'N/A'}")
        if event.event == RunEvent.run_content:
            print(f"  Content: {event.content}")
        if event.event == RunEvent.tool_call_completed:
            print(f"  Tool Completed: {event.tool.tool_name if event.tool else 'N/A'}")
            print(f"  Result: {str(event.tool.result)[:100] if event.tool and event.tool.result else 'N/A'}...")

if __name__ == "__main__":
    test_stream()
