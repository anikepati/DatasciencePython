import asyncio
import os
from typing import Any

from google.adk.agents import LlmAgent, tool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types  # Used for Content objects, even with OpenAI via LiteLLM
import base64
from openai import OpenAI  # For the custom tool

# Custom tool to analyze a saved screenshot with OpenAI vision
@tool
def vision_analyze(filename: str) -> str:
    """
    Analyzes a screenshot file using OpenAI vision to describe content or suggest coordinates.
    Args:
        filename: The screenshot filename (e.g., 'page.png') saved by browser_take_screenshot.
    Returns:
        Description and suggested coordinates (e.g., for mouse clicks).
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    
    image_path = os.path.join('./screenshots', filename)
    if not os.path.exists(image_path):
        return "Error: Screenshot file not found."
    
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    base64_image = base64.b64encode(image_data).decode('utf-8')
    
    # Prompt OpenAI for vision analysis (customize as needed)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this screenshot: Describe the layout, key elements, and suggest absolute coordinates (x, y) for interactive elements like buttons or fields. Viewport is standard."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"  # Assumes PNG; adjust for JPG
                        }
                    }
                ]
            }
        ],
        max_tokens=500  # Adjust as needed
    )
    return response.choices[0].message.content

async def get_tools_async() -> tuple[list[Any], Any]:
    # Connect to running Playwright-MCP server via SSE
    connection_params = SseConnectionParams(
        url="http://localhost:8931/mcp",
        headers={},
        timeout=30
    )
    
    toolset = McpToolset(connection_params=connection_params)
    tools = await toolset.get_tools()
    
    # Add custom vision tool
    tools.append(vision_analyze)
    
    return tools, toolset

async def get_agent_async() -> tuple[LlmAgent, Any]:
    tools, toolset = await get_tools_async()
    
    agent = LlmAgent(
        model=LiteLlm(model="openai/gpt-4o"),  # Explicitly use LiteLLM with OpenAI GPT-4o for all completions
        name="enterprise_browser_agent",
        instruction="""
        You are an enterprise browser agent using Playwright tools.
        - For interactions, use browser_snapshot for structured accessibility data.
        - For visual verification or vision-based tasks, use browser_take_screenshot to save an image, then call vision_analyze on the filename to get a description or coordinates.
        - Use coordinate tools like browser_mouse_click_xy if vision analysis suggests specific (x, y) positions.
        - Do not use snapshots if the task requires visual pixel-level analysis (e.g., colors, layouts not in accessibility tree).
        - Always specify a unique filename in browser_take_screenshot (e.g., 'page.png').
        - Handle enterprise auth via loaded storage state.
        """,
        tools=tools,
    )
    return agent, toolset

# Multi-turn chat completion example using Runner and sessions
async def main():
    agent, toolset = await get_agent_async()
    
    # Set up session for multi-turn chat
    session_service = InMemorySessionService()
    session = session_service.create_session(app_name="browser_app", user_id="user1", session_id="chat_session1")
    runner = Runner(agent=agent, app_name="browser_app", session_service=session_service)
    
    try:
        # First turn: Initial query
        initial_msg = types.Content(role="user", parts=[types.Part(text="Navigate to https://example.com and take a screenshot named 'example.png'.")])
        print("First turn response:")
        for event in runner.run(user_id="user1", session_id="chat_session1", new_message=initial_msg):
            if event.is_final_response() and event.content:
                print(event.content.parts[0].text.strip())
        
        # Second turn: Follow-up query (multi-turn, maintains context)
        follow_up_msg = types.Content(role="user", parts=[types.Part(text="Now analyze the screenshot with vision and suggest coordinates for the main button.")])
        print("\nSecond turn response:")
        for event in runner.run(user_id="user1", session_id="chat_session1", new_message=follow_up_msg):
            if event.is_final_response() and event.content:
                print(event.content.parts[0].text.strip())
        
        # Additional turns can be added similarly...
    
    finally:
        await toolset.close()  # Clean up the toolset

if __name__ == "__main__":
    asyncio.run(main())
