This is a robust, enterprise-ready implementation using the **Google Agent Development Kit (ADK)**. It correctly adheres to the "Amnesiac" pattern (stateless execution) to prevent context window exhaustion, relying on the `StateStore` and `Workflow` to drive progress rather than the LLM's memory.

### 📂 Project Structure

```text
browser_agent/
├── app.py                  # Entry point
├── .env                    # Secrets (API Keys)
├── requirements.txt        # Dependencies
├── workflow.py             # Deterministic steps
├── agent/
│   ├── __init__.py
│   ├── agent_factory.py    # Assembles the ADK Agent + Plugins
│   ├── model.py            # LLM Configuration
│   └── prompt.py           # Step-specific prompt builder
├── mcp/
│   ├── __init__.py
│   └── playwright.py       # MCP Toolset Configuration
├── runner/
│   ├── __init__.py
│   └── step_runner.py      # Execution loop with retry & pruning
└── state/
    ├── __init__.py
    └── store.py            # Durable State Management

```

---

### 📦 1. Configuration & Dependencies

**`requirements.txt`**

```text
google-adk>=0.1.0
python-dotenv

```

**`.env`**

```text
GOOGLE_API_KEY=your_gemini_api_key

```

---

### 🧭 2. Workflow Definition

**`workflow.py`**
This defines the "Business Logic" separately from the "AI Logic."

```python
WORKFLOW = [
    "Go to https://admin.powerapps.microsoft.com",
    "Click Manage in the left navigation",
    "Click Environments",
    "Select the environment named SSMS",
    "Click See all under Business Units",
    "Click New Business Unit",
    "Wait for the panel to load",
    "Enter parent business unit name",
    "Click Save",
]

```

---

### 🧠 3. Agent Configuration

**`agent/model.py`**
Configures the specific LLM parameters.

```python
import os
from google.adk.models.lite_llm import LiteLlm

def execution_model():
    # Ensure API key is loaded in environment
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError("GOOGLE_API_KEY is missing from .env")
        
    return LiteLlm(
        model="gemini-2.5-flash",
        temperature=0.0,      # Strict deterministic output
        max_tokens=512,       # Cap output to prevent rambling
    )

```

**`agent/prompt.py`**
Constructs a fresh prompt for every step.

```python
def build_step_prompt(step_index: int, instruction: str, state: dict) -> str:
    return f"""
You are a deterministic browser automation agent.

Current step sequence: {step_index + 1}

Instruction:
{instruction}

Known state (read-only):
{state}

Rules:
- Execute ONLY this step.
- Do NOT plan ahead.
- Do NOT repeat previous steps.
- Prefer vision-based interaction (coordinate clicks) over DOM selectors if possible.
- If the step is already complete based on the visual state, reply exactly with STEP_ALREADY_DONE.
"""

```

**`agent/agent_factory.py`**
Assembles the agent with the **Context Filter Plugin**. This is the critical component that drops old HTML snapshots from the context window.

```python
from google.adk.agents import LlmAgent
from google.adk.plugins.context_filter import ContextFilterPlugin
from agent.model import execution_model

def create_agent(tools):
    # The 'Amnesiac' filter: keeps only the system prompt + last interaction
    context_filter = ContextFilterPlugin(
        keep_system_messages=True,
        keep_last_n_model_messages=1,
        keep_last_n_tool_results=1,
        drop_all_other_events=True,
    )

    return LlmAgent(
        model=execution_model(),
        tools=tools,
        plugins=[context_filter],
        system_instruction=(
            "You are a stateless browser automation executor. "
            "You only act on the current instruction based on the current screen."
        ),
    )

```

---

### 🌐 4. Tooling (MCP)

**`mcp/playwright.py`**
Uses the standard Model Context Protocol via `npx`.

```python
from google.adk.tools.mcp_toolset import MCPToolset
import shutil

def create_playwright_toolset():
    # Verify npx is installed
    if not shutil.which("npx"):
        raise RuntimeError("npx not found. Please install Node.js and npm.")

    return MCPToolset(
        server_command=[
            "npx",
            "-y",
            "@playwright/mcp@latest",
            "--headless",
            "--caps=vision",          # Enable Screenshot capabilities
            "--snapshot-mode=none",   # Disable heavy DOM snapshots
        ]
    )

```

---

### 🧾 5. State Management

**`state/store.py`**
Pure Python state storage. In a real enterprise app, this would connect to Redis or SQL.

```python
class StateStore:
    def __init__(self):
        self.state = {
            "step": 0,
            "logged_in": False,
            "current_env": None,
            "last_error": None
        }

    def get(self):
        return dict(self.state)

    def advance(self):
        self.state["step"] += 1

    def update(self, updates: dict):
        self.state.update(updates)

```

---

### ▶️ 6. The Runner (Core Logic)

**`runner/step_runner.py`**
Handles retries and session pruning to keep memory footprint O(1).

```python
from agent.prompt import build_step_prompt
import time

MAX_RETRIES = 3

def prune_session(session_service, session_id):
    """
    Manually ensures the session object does not grow indefinitely 
    in the backing store (memory/DB).
    """
    session = session_service.get_session(session_id)
    if not session:
        return

    # Keep only the last 3 events to support the ContextFilterPlugin
    # 1. System Prompt
    # 2. Last User Prompt
    # 3. Last Agent Response
    if len(session.events) > 3:
        session.events = session.events[-3:]
        
        # Explicit save if the service supports it (persisting the prune)
        if hasattr(session_service, 'save_session'):
            session_service.save_session(session)

def run_workflow(runner, workflow, state_store, session_id, session_service):
    print(f"Starting workflow with {len(workflow)} steps.")

    while state_store.get()["step"] < len(workflow):
        step_idx = state_store.get()["step"]
        instruction = workflow[step_idx]
        
        print(f"\n--- Step {step_idx + 1}: {instruction} ---")

        retries = 0
        success = False

        while retries < MAX_RETRIES:
            prompt = build_step_prompt(
                step_index=step_idx,
                instruction=instruction,
                state=state_store.get(),
            )

            try:
                # ADK Runner Execution
                result = runner.run(
                    input=prompt,
                    session_id=session_id,
                )
                
                output_text = result.output_text or ""

                if "STEP_ALREADY_DONE" in output_text:
                    print("✓ Step already completed (detected by agent).")
                    success = True
                    break

                if result.is_success:
                    print("✓ Agent execution successful.")
                    success = True
                    break
                else:
                    print(f"⚠ Step failed (Attempt {retries + 1}/{MAX_RETRIES})")

            except Exception as e:
                print(f"⚠ Execution error: {e}")
            
            retries += 1
            time.sleep(2) # Backoff

        if not success:
            raise RuntimeError(f"Workflow failed at step {step_idx + 1}: {instruction}")

        # Move to next step
        state_store.advance()

        # 🔥 CRITICAL: Prune session to prevent token bloat
        prune_session(session_service, session_id)

```

---

### 🚀 7. Application Entry Point

**`app.py`**

```python
import os
from dotenv import load_dotenv

# Load env vars before importing agent components
load_dotenv()

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from workflow import WORKFLOW
from mcp.playwright import create_playwright_toolset
from agent.agent_factory import create_agent
from runner.step_runner import run_workflow
from state.store import StateStore

def main():
    print("🚀 Initializing Enterprise Browser Agent (Google ADK)...")

    # 1. Setup Tools
    try:
        tools = create_playwright_toolset()
    except Exception as e:
        print(f"❌ Failed to init MCP tools: {e}")
        return

    # 2. Setup Agent
    agent = create_agent(tools)

    # 3. Setup Infrastructure
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        session_service=session_service,
    )
    state_store = StateStore()
    
    session_id = "browser-automation-001"

    # 4. Run
    try:
        run_workflow(
            runner=runner,
            workflow=WORKFLOW,
            state_store=state_store,
            session_id=session_id,
            session_service=session_service,
        )
        print("\n✅ WORKFLOW COMPLETED SUCCESSFULLY")
        
    except Exception as e:
        print(f"\n❌ WORKFLOW FAILED: {e}")

if __name__ == "__main__":
    main()

```

This video covers the fundamental setup of the Agent Development Kit which this code is based on:
... [Getting started with Agent Development Kit](https://www.youtube.com/watch?v=44C8u0CDtSo) ...

The video is relevant because it provides a foundational walkthrough of the Agent Development Kit, which is the exact framework used in this solution.
