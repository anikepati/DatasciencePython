import os
import subprocess
import time
import asyncio
import win32security
import win32con
import win32api
from google.adk import Agent, MCPToolset

# ================================================================
# CONFIGURATION SECTION
# ================================================================

DIGITAL_ID_USER = "DigitalIDUser"        # your domain username
DIGITAL_ID_DOMAIN = "MYDOMAIN"           # your AD domain
DIGITAL_ID_PASSWORD = "SecretPassword"   # avoid hardcoding in prod!
MCP_PORT = 5001                          # port where MCP will run
MCP_URL = f"http://localhost:{MCP_PORT}"


# ================================================================
# FUNCTION: Launch MCP under digital ID identity
# ================================================================

def start_mcp_as_digital_id():
    print("🔹 Starting Playwright MCP server under digital ID...")

    # Log on as the digital ID user
    handle = win32security.LogonUser(
        DIGITAL_ID_USER,
        DIGITAL_ID_DOMAIN,
        DIGITAL_ID_PASSWORD,
        win32con.LOGON32_LOGON_INTERACTIVE,
        win32con.LOGON32_PROVIDER_DEFAULT
    )

    # Impersonate the logged-on user
    win32security.ImpersonateLoggedOnUser(handle)

    env = os.environ.copy()

    # Start the MCP server as a subprocess under this identity
    subprocess.Popen(
        ["npx", "@playwright/mcp@latest", "--port", str(MCP_PORT)],
        env=env,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    # Revert impersonation immediately after launch
    win32security.RevertToSelf()
    handle.Close()

    print(f"✅ MCP launched at {MCP_URL} as {DIGITAL_ID_DOMAIN}\\{DIGITAL_ID_USER}")


# ================================================================
# FUNCTION: Run ADK Agent and Playwright actions
# ================================================================

async def run_agent_actions():
    # Wait a few seconds for MCP to initialize
    print("⏳ Waiting for MCP to start...")
    time.sleep(5)

    # Connect ADK agent to Playwright MCP
    print("🔹 Connecting ADK agent to Playwright MCP...")
    mcp = MCPToolset(MCP_URL)

    agent = Agent(
        name="digital_id_agent",
        description="Google ADK + Playwright MCP under Digital ID for Windows Auth",
        toolset=mcp
    )

    # Use Playwright tools
    browser = await agent.tools.browser.new_context()
    page = await browser.new_page()

    # Go to a Windows Auth–protected URL
    target_url = "https://intranet.mycompany.local"
    print(f"🌐 Navigating to: {target_url}")
    await page.goto(target_url)

    # Print content snippet
    html = await page.content()
    print("✅ Page content fetched successfully (first 300 chars):")
    print(html[:300])

    await browser.close()


# ================================================================
# MAIN ENTRY
# ================================================================

if __name__ == "__main__":
    start_mcp_as_digital_id()
    asyncio.run(run_agent_actions())
