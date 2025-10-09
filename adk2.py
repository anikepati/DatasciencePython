You can drop these into your project (adjust imports / paths as needed) and run them.

utils.py
# utils.py

import os
import json
from google.genai import types
from google.genai.types import Part
from typing import List, Dict, Any, Optional

def image_to_parts(filepath: str, prompt: str) -> List[Part]:
    """Converts a local image file to a multimodal list of Parts for Gemini Vision + prompt."""
    try:
        with open(filepath, "rb") as f:
            img_bytes = f.read()
        image_part = Part.from_bytes(data=img_bytes, mime_type="image/png")
        text_part = types.Part.from_text(prompt)
        return [image_part, text_part]
    except FileNotFoundError:
        # If screenshot is missing, we at least return a text-only part so Gemini can reason
        return [types.Part.from_text(f"Error: screenshot missing. Prompt: {prompt}")]

def create_temp_screenshot_dir():
    os.makedirs("temp_screenshots", exist_ok=True)

def parse_correction_json(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse the Gemini response to extract the JSON object containing diagnosis & corrected_data.
    Returns a dict or None if parsing fails or corrected_data is missing.
    """
    # Try to find a JSON block enclosed in ```json … ```
    start = response_text.find("```json")
    end = response_text.find("```", start + 1) if start != -1 else -1

    json_str = None
    if start != -1 and end != -1:
        json_str = response_text[start + len("```json"):end].strip()
    else:
        # fallback: try to parse the entire response as JSON
        json_str = response_text.strip()

    try:
        obj = json.loads(json_str)
    except json.JSONDecodeError:
        print("⚠️ Warning: Unable to parse JSON from Gemini response:", response_text)
        return None

    # Basic validation
    if "diagnosis" not in obj or "corrected_data" not in obj:
        print("⚠️ Warning: Parsed JSON missing required keys:", obj)
        return None

    return obj

tools.py
# tools.py

import pandas as pd
import time
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from utils import create_temp_screenshot_dir

def read_user_data_from_excel(filepath: str, sheet_name: str = "Sheet1") -> list[dict]:
    df = pd.read_excel(filepath, sheet_name=sheet_name)
    required = ["Email", "Country", "Gender"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"Column '{c}' not found in Excel sheet.")
    # Drop rows missing Email (as that's essential)
    df2 = df.dropna(subset=["Email"])
    records = df2[required].to_dict(orient="records")
    return records

def register_user_on_web(user_data: dict, url: str) -> dict:
    """
    Try to register using the data. Returns a dict with:
      - status: "SUCCESS" or "FAILURE"
      - message: short textual info
      - user_data: the data used
      - maybe: screenshot_path (on failure)
    """
    email = user_data.get("Email", "")
    country = user_data.get("Country", "")
    gender = user_data.get("Gender", "")
    screenshot_path = None

    create_temp_screenshot_dir()

    print(f"[Tool] Attempting registration: {email} / {country} / {gender}")

    browser = None
    page = None
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            # You may adjust timeouts / navigation behavior here
            page.set_default_timeout(10000)
            page.goto(url)

            # Fill email
            page.get_by_role("textbox", name="Email Address").fill(email)

            # Select country from dropdown (by visible label, or value)
            page.get_by_label("Country").select_option(label=country)

            # Select gender (assuming radio button or label matching)
            page.get_by_label(gender, exact=True).check()

            # Submit
            page.get_by_role("button", name="Submit").click()

            # Wait for navigation or success indicator
            # You might prefer waiting for a particular success element instead
            page.wait_for_timeout(3000)

            # Determine success: if URL changed or specific element appears
            if page.url != url:
                return {
                    "status": "SUCCESS",
                    "message": f"Registration appears successful for {email}.",
                    "user_data": user_data
                }
            else:
                # No URL change, assume failure
                raise RuntimeError("Form submission did not result in navigation or success change.")

    except Exception as e:
        # On failure, capture screenshot if possible
        timestamp = int(time.time())
        safe_email = email.replace("@", "_at_").replace(".", "_dot_")
        screenshot_path = f"temp_screenshots/error_{timestamp}_{safe_email}.png"
        try:
            if page:
                page.screenshot(path=screenshot_path)
        except Exception as e2:
            print("[Tool] Could not capture screenshot:", e2)
        finally:
            if browser:
                try:
                    browser.close()
                except:
                    pass

        return {
            "status": "FAILURE",
            "message": f"Submission failed: {repr(e)}",
            "user_data": user_data,
            "screenshot_path": screenshot_path
        }
    finally:
        # Extra safety: ensure browser closed
        if browser:
            try:
                browser.close()
            except:
                pass

agent.py
# agent.py

import os
import json
from google.adk.agents import Agent
from google.adk.client import Client
from google.genai import types

from tools import register_user_on_web, read_user_data_from_excel
from utils import image_to_parts, parse_correction_json

ADK_CLIENT = Client()

def analyze_screenshot_error(screenshot_path: str, user_data: dict, error_message: str) -> str:
    """
    Calls Gemini Vision + Reasoning to diagnose and propose corrected user_data.
    Returns a JSON string (single object) with keys: "diagnosis" and "corrected_data" (or null).
    """
    if not os.path.exists(screenshot_path):
        return json.dumps({
            "diagnosis": "Screenshot path not found: " + screenshot_path,
            "corrected_data": None
        })

    # Prepare prompt
    data_str = json.dumps(user_data, indent=2)
    prompt = f"""
You are a QA engineer. A web registration failed with this user_data:
{data_str}
Error message: "{error_message}"

1. Diagnose what the screenshot likely shows (e.g. invalid format, missing field, incorrect selection).
2. Provide corrected user_data (only if you are confident) as full JSON, else null.

Output exactly a single JSON object with:
  - diagnosis: a textual explanation
  - corrected_data: full JSON data object or null

Do *not* include any other markdown or text outside the JSON.

"""

    parts = image_to_parts(screenshot_path, prompt)

    response = ADK_CLIENT.models.generate_content(
        model="gemini-2.5-pro",
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction="You are expert in UI error diagnosis. Output a single JSON only."
        )
    )

    # Optionally remove screenshot to save space
    try:
        os.remove(screenshot_path)
    except Exception:
        pass

    return response.text

# Define the Agent
RegistrationAgent = Agent(
    name="self_correcting_registration_agent",
    model="gemini-2.5-pro",
    instruction=(
        "You are an autonomous web registration agent with self-correction capability. "
        "1. Use `read_user_data_from_excel` to load users. "
        "2. For each user, attempt `register_user_on_web`. "
        "3. If the first attempt fails, call `analyze_screenshot_error` with screenshot, original data, and error message. "
        "4. Parse the JSON response. If it has `corrected_data` not null, you must immediately call `register_user_on_web` again with the corrected data (only once per user). "
        "5. Build a consolidated report, for each user: original data, first attempt result, diagnosis (if any), corrected data (if any), second attempt result. "
        "Return the final report."
    ),
    tools=[read_user_data_from_excel, register_user_on_web, analyze_screenshot_error]
)

run.py
# run.py

import os
import asyncio
from dotenv import load_dotenv
from google.adk.client import Client
from google.adk.agents.run_config import RunConfig
from agent import RegistrationAgent

load_dotenv()
if "GEMINI_API_KEY" not in os.environ:
    raise RuntimeError("GEMINI_API_KEY not found in environment.")

# Adjust to your real registration URL
REGISTRATION_URL = "https://your-registration-site.com/signup"

async def main():
    prompt = (
        "Using the read_user_data_from_excel tool, read users from 'data/users.xlsx'. "
        f"For each user, attempt registration on '{REGISTRATION_URL}'. "
        "If the first try fails, call analyze_screenshot_error to get a correction, and if a corrected_data is proposed, retry once. "
        "Finally, return a combined report of all attempts."
    )

    print("=== Starting Self-Correcting Registration Agent ===")
    print("Target URL:", REGISTRATION_URL)

    client = Client()
    result = await client.agents.arun(
        agent=RegistrationAgent,
        prompt=prompt,
        config=RunConfig(stream=True)
    )

    print("\n=== FINAL REPORT ===")
    print(result.content.text)

if __name__ == "__main__":
    asyncio.run(main())

How This Works — Flow Summary

Agent is invoked with the driving prompt.

Agent calls read_user_data_from_excel, gets a list of user dicts.

For each user:

a. Agent calls register_user_on_web(user_data, url).
b. If the result is "SUCCESS", record it and move on.
c. If "FAILURE", take the screenshot_path, user_data, and message and call analyze_screenshot_error(...).
d. Parse the JSON output via parse_correction_json.
e. If parsed JSON has corrected_data (and not null), call register_user_on_web(corrected_data, url) once more.
f. Record final outcome (success or failure) along with the diagnosis.
g. If no correction or parsing fails, skip retry and just record failure + diagnosis.

After all users, the agent collates a final report (for each user: original, first attempt, diagnosis, corrected_data, second attempt).

Agent returns the report as its final content.

Example of Expected Final Report Format

The final output might look like:

User: alice@example.com
 • First attempt: FAILURE — Submission failed: “Invalid format for Gender”
 • Diagnosis: “The screenshot shows error message: ‘Invalid gender selection: must be Male or Female’”
 • Corrected_data: {"Email":"alice@example.com","Country":"USA","Gender":"Female"}
 • Second attempt: SUCCESS — Registration appears successful

User: bob@example.com
 • First attempt: SUCCESS — Registration appears successful

User: charlie@example.com
 • First attempt: FAILURE — Submission failed: “Timeout / page did not change”
 • Diagnosis: “Could not detect any validation error in the screenshot; the page may be frozen or script blocked”
 • Corrected_data: null
 • No second attempt attempted


You could also instruct the agent to output JSON or Excel of the report instead of human-readable text.

Notes & Further Recommendations

Adjust success detection logic: Relying on URL change is simplistic. Many forms use AJAX. You may need to wait for a success banner, check for absence of error messages, or check network responses. Modify register_user_on_web accordingly.

Timeouts & long waits: In complex forms, you may need to wait for dynamic JS or validation. Consider waiting for “success indicator element” instead of fixed timeout.

Multiple retry levels: If the correction still fails, you could allow a second correction attempt (e.g. ask vision again) or escalate to human fallback. But for safety, I limit to one correction attempt per user to avoid loops.

Structured report as JSON: If you prefer machine-readable output, change the agent’s final output to a JSON list of user records with nested fields.

Rate limiting / delays: If the registration endpoint has throttling or rate limits, introduce delays or pacing between attempts.

Edge cases:

If the screenshot is blank or error message not visible, vision tool may return corrected_data: null.

If the correction proposes invalid fields (e.g. missing required field), ensure you validate before reattempting.

If the registration page logic changes (labels, element names), the selectors (“get_by_role”, “get_by_label”) may fail — you may need more robust locator strategies (XPath, CSS selectors, fallback tries).

Security / Captcha: If the site employs CAPTCHA, vision alone may be insufficient; you’ll need a fallback human-in-the-loop or an anti-captcha tool. In those cases, corrected_data: null is the right response, and you log “requires human input.”

Cleaning up: I delete the screenshot after diagnosing to avoid clutter; you may choose to keep them for audit or debugging.

Logging / telemetry: Add more structured logging (to a file, JSON logs) so you can introspect what corrections were made and how often.

How to Test & Run

Populate data/users.xlsx with sample rows including “Email”, “Country”, “Gender”.

Make sure your target registration URL is live and accessible.

Set GEMINI_API_KEY in .env.

Install dependencies:

pip install google-adk pandas openpyxl playwright python-dotenv
playwright install chromium


Run python run.py.

Observe console logs, and inspect the final report. If errors occur, inspect the generated screenshots in temp_screenshots/.
