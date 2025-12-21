```python
import asyncio
import contextlib
import logging

# Google ADK Imports
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.models import Gemini
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.types.context import Context
from google.genai import types, Client

# MCP Imports (Model Context Protocol)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# --- CONFIGURATION ---
API_KEY = "YOUR_GEMINI_API_KEY"  # Replace with actual key
MODEL_MAIN = "gemini-1.5-pro-latest" # Powerful model for reasoning
MODEL_FAST = "gemini-1.5-flash"      # Cheap model for summarization

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BrowserAgent")

# ==============================================================================
# PART 1: THE INTELLIGENCE (Filter & Summarizer)
# ==============================================================================

class SmartContextFilter(BasePlugin):
    """
    Implements the "One-Snapshot Rule":
    - Finds the MOST RECENT Playwright snapshot in the history.
    - Keeps it intact (so the LLM can see the current screen).
    - Scrubs ALL previous snapshots to save tokens.
    """
    def before_model_callback(self, context: Context, **kwargs):
        history = context.history
        latest_snapshot_idx = -1

        # 1. Backward pass: Find the index of the newest snapshot
        for i in range(len(history) - 1, -1, -1):
            event = history[i]
            # Detect tool response from Playwright snapshot tools
            if event.type == "tool_response" and "snapshot" in event.tool_name:
                latest_snapshot_idx = i
                break

        # 2. Forward pass: Scrub everything that isn't the newest
        scrub_count = 0
        for i, event in enumerate(history):
            if event.type == "tool_response" and "snapshot" in event.tool_name:
                
                # If this is the latest one, preserve it.
                if i == latest_snapshot_idx:
                    logger.info(f"👀 KEEPING active snapshot at index {i} for reasoning.")
                    continue 

                # Otherwise, scrub it if not already scrubbed
                if "[History Cleaned]" not in str(event.content):
                    event.content = "[History Cleaned: Old page state removed to save context.]"
                    scrub_count += 1
        
        if scrub_count > 0:
            logger.info(f"🧹 Scrubbed {scrub_count} old snapshots from context.")
        
        return context

# The prompt that prevents "State Amnesia" during compaction
STATE_AWARE_PROMPT = """
You are the memory manager for a browser agent. 
Summarize the oldest events into a concise narrative.

CRITICAL INSTRUCTIONS:
1. **PRESERVE VARIABLES:** If the agent typed a specific username, password, or search query, KEEP IT EXACTLY.
2. **TRACK ERRORS:** If an action failed, record the error message.
3. **COMPRESS NOISE:** Summarize navigation like "Clicked Next 3 times" or "Scrolled down".
4. **DROP HTML:** Do not mention specific DOM IDs (like #div-123) unless necessary for an error.

History to summarize:
{history}
"""

# ==============================================================================
# PART 2: THE INFRASTRUCTURE (MCP Bridge)
# ==============================================================================

class McpBridge:
    """
    Connects ADK to the Playwright MCP Server.
    """
    def __init__(self):
        # We assume the user has installed @playwright/mcp via npm
        self.server_params = StdioServerParameters(
            command="npx", 
            args=["-y", "@playwright/mcp@latest"]
        )
        self.session = None
        self.exit_stack = contextlib.AsyncExitStack()
        self.tool_map = {}

    async def start(self):
        logger.info("🔌 Connecting to Playwright MCP Server...")
        read, write = await self.exit_stack.enter_async_context(
            stdio_client(self.server_params)
        )
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.session.initialize()
        
        # Fetch tools and map them for ADK
        tools_list = await self.session.list_tools()
        gemini_tools = []
        
        for tool in tools_list.tools:
            self.tool_map[tool.name] = tool.name
            
            # Convert MCP Tool -> Gemini Function Declaration
            gemini_tools.append(types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema
            ))
            
        logger.info(f"✅ Loaded {len(gemini_tools)} tools from Playwright.")
        return gemini_tools

    async def execute_tool(self, tool_name, tool_args):
        """Execute tool and return string result."""
        try:
            result = await self.session.call_tool(tool_name, arguments=tool_args)
            # Join text content from result
            return "\n".join([c.text for c in result.content if hasattr(c, 'text')])
        except Exception as e:
            return f"Tool Error: {str(e)}"

    async def cleanup(self):
        await self.exit_stack.aclose()

# ==============================================================================
# PART 3: THE MAIN APPLICATION
# ==============================================================================

async def main():
    # 1. Initialize Infrastructure
    bridge = McpBridge()
    tools_declarations = await bridge.start()
    
    # 2. Define the 'Executer' function for ADK
    # ADK needs a way to call the tools when the model asks for them.
    async def tool_execution_handler(tool_call):
        return await bridge.execute_tool(tool_call.name, tool_call.args)

    # 3. Define the Models
    main_model = Gemini(model=MODEL_MAIN, api_key=API_KEY)
    summary_model = Gemini(model=MODEL_FAST, api_key=API_KEY)

    # 4. Configure the Summarizer (Brain Part A)
    summarizer = LlmEventSummarizer(
        llm=summary_model,
        prompt_template=STATE_AWARE_PROMPT
    )

    # 5. Build the App (Brain Part B)
    app = App(
        name="BrowserAgent_v1",
        # We inject the tool definitions into the root agent
        root_agent_config={
            "model": main_model,
            "tools": tools_declarations,
            "system_instruction": "You are an autonomous browser agent. Use the available tools to navigate."
        },
        
        # PLUGINS: Register our Smart Context Filter
        plugins=[SmartContextFilter()],
        
        # COMPACTION: Configure the Memory Window
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=1,    # Check every step
            window_size=5,            # Keep last 5 steps (and the LATEST snapshot)
            summarizer=summarizer     # Compress the rest
        ),
        
        # LINKER: Connects the abstract 'tool calls' to our actual MCP Bridge
        tool_execution_callback=tool_execution_handler
    )

    # 6. Run the Agent
    print("\n🚀 Agent Started. Type 'exit' to quit.\n")
    
    # Initial task
    user_query = "Navigate to google.com and search for 'Context Filtering in AI'"
    
    try:
        # Run the app (ADK handles the loop, the filtering, and the summarizing)
        result = await app.run_async(prompt=user_query)
        print(f"\n🏁 Final Result: {result.text}")
        
    except Exception as e:
        logger.error(f"Runtime Error: {e}")
    finally:
        await bridge.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```
