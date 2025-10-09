That's an excellent step toward building a truly autonomous agent! Using callbacks allows the Gemini Agent to re-invoke the web automation tool with corrected data immediately after the Vision tool diagnoses an error. This creates a powerful self-correction loop 🔄.

The Agent Development Kit (ADK) handles the core mechanism for tool use and response, but to enforce the data correction loop, we'll use a specific strategy:

The analyze_screenshot_error tool will be instructed to return the corrected data in a structured format (JSON).

The Agent's main instruction will be updated to explicitly say: "If a correction is provided by the vision tool, attempt the submission again with the corrected data."

Here is the revised, modular code focusing on the self-correction callback mechanism.

1. Project Updates and New Dependencies
We'll use Python's built-in json module to handle the structured output for corrections.

⚙️ Dependencies and Setup
Ensure you have the ADK client, pandas, and playwright installed.

Bash

uv pip install google-adk pandas openpyxl playwright python-dotenv
uvx playwright install chromium
📂 File Structure (Unchanged)
project_root/
├── .env
├── data/
│   └── users.xlsx
├── agent.py
├── tools.py
├── utils.py
└── run.py
2. Revised Modular Code
utils.py (Data & Image Handling)
We add a function to parse the structured JSON response from the agent.

Python

# utils.py
import os
import json
from google.genai import types
from google.genai.types import Part
from typing import List, Dict, Any

# --- Image Handling (Unchanged) ---
def image_to_parts(filepath: str, prompt: str) -> List[Part]:
    """Converts a local image file to a multimodal list of Parts for Gemini."""
    try:
        with open(filepath, "rb") as image_file:
            image_bytes = image_file.read()
        image_part = Part.from_bytes(data=image_bytes, mime_type='image/png')
        return [image_part, types.Part.from_text(prompt)]
    except FileNotFoundError:
        return [types.Part.from_text(f"Error: Image file not found at {filepath}. Original prompt was: {prompt}")]

def create_temp_screenshot_dir():
    """Ensures the temp_screenshots directory exists."""
    os.makedirs("temp_screenshots", exist_ok=True)

# --- New Function for Structured Output Parsing ---
def parse_correction_json(text: str) -> Dict[str, Any] | None:
    """Extracts and parses the structured JSON correction from the Gemini text response."""
    try:
        # Gemini often wraps the JSON in markdown blocks
        start = text.find("```json")
        end = text.find("```", start + 1)
        
        if start != -1 and end != -1:
            json_str = text[start + 7:end].strip()
        else:
            # Assume the entire response might be the JSON string if no markdown is found
            json_str = text.strip()

        return json.loads(json_str)
    except json.JSONDecodeError:
        print("Warning: Could not parse JSON correction from Gemini response.")
        return None
tools.py (Web Automation & Data Reading)
These tools remain essentially the same, as their job is just to execute the action or read the data.

Python

# tools.py
import pandas as pd
from playwright.sync_api import sync_playwright
import os
import time
from .utils import create_temp_screenshot_dir

# --- read_user_data_from_excel (Unchanged) ---
def read_user_data_from_excel(filepath: str, sheet_name: str = 'Sheet1') -> list[dict]:
    """Reads a list of user registration data (Email, Country, Gender) from Excel."""
    df = pd.read_excel(filepath, sheet_name=sheet_name)
    required_cols = ['Email', 'Country', 'Gender']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in Excel sheet.")
            
    user_data = df[required_cols].dropna(subset=['Email']).to_dict('records')
    return user_data

# --- register_user_on_web (Revised Input/Output) ---
def register_user_on_web(user_data: dict, url: str) -> dict:
    """
    Navigates to a registration URL, fills the form, and returns result or failure 
    with a screenshot path.

    The input argument is now a single user dictionary to support the self-correction callback.
    """
    email = user_data.get('Email', 'UNKNOWN')
    country = user_data.get('Country', '')
    gender = user_data.get('Gender', '')
    screenshot_path = None
    
    create_temp_screenshot_dir()

    print(f"\nAttempting registration for: {email} (Country: {country}, Gender: {gender})")

    try:
        with sync_playwright() as p:
            # We use headless=False here to potentially see the correction attempt
            browser = p.chromium.launch(headless=True) 
            page = browser.new_page()
            page.goto(url)
            
            # Use user-facing locators
            page.get_by_role("textbox", name="Email Address").fill(email)
            page.get_by_label("Country").select_option(label=country)
            page.get_by_label(gender, exact=True).check()
            
            page.get_by_role("button", name="Submit").click()
            
            # Wait for success or error to manifest
            page.wait_for_timeout(3000) 

            # Placeholder success check (adjust for your real site)
            if page.url != url:
                 browser.close()
                 return {"status": "SUCCESS", "message": f"Successfully submitted email: {email}."}
            else:
                 # Raise a generic exception to force the screenshot logic
                 raise Exception("Submission failed. Form did not submit or navigation did not occur.")

    except Exception as e:
        timestamp = int(time.time())
        screenshot_path = f"temp_screenshots/error_{timestamp}_{email.replace('@', '_at_')}.png"
        
        # Take the screenshot on error
        try:
            page.screenshot(path=screenshot_path)
        except Exception:
            pass # Ignore if page is already closed/invalid
        finally:
             if 'browser' in locals() and not browser.is_closed():
                 browser.close()
        
        return {
            "status": "FAILURE",
            "message": f"Submission failed for {email}. Reason: {e}",
            "user_data": user_data, # Return the original data for logging
            "screenshot_path": screenshot_path
        }
agent.py (The Self-Correction Logic)
The core change is in the analyze_screenshot_error tool's instructions to the model, asking for a structured JSON correction. The Agent's instruction is also updated to use this capability.

Python

# agent.py
import os
import json
from google.adk.agents import Agent
from google.genai import types
from google.adk.client import Client

# Import all tools and utilities
from .tools import register_user_on_web, read_user_data_from_excel
from .utils import image_to_parts, parse_correction_json

# Initialize client to use for vision tool
ADK_CLIENT = Client() 

def analyze_screenshot_error(screenshot_path: str, user_data: dict, error_message: str) -> str:
    """
    Tool that uses Gemini Vision to diagnose a web error and suggest a structured correction.

    Args:
        screenshot_path: The local path to the PNG image file.
        user_data: The data that caused the error (Email, Country, Gender).
        error_message: The technical error message from Playwright.
        
    Returns:
        A structured JSON string containing the diagnosis and the corrected user_data.
    """
    if not os.path.exists(screenshot_path):
        return json.dumps({"diagnosis": "Screenshot not found.", "corrected_data": None})

    current_data_str = json.dumps(user_data, indent=2)
    
    prompt = f"""
    Analyze the provided screenshot and the current user data that failed:
    {current_data_str}

    The technical error was: "{error_message}".

    1. **Diagnosis**: Explain the root cause of the visible error (e.g., missing field, invalid format, invisible element).
    2. **Correction**: If a correction can be made to the data (e.g., changing 'Invalid' to 'Female' or fixing an email typo), provide the complete, corrected user data in the `corrected_data` field. If the error is unrecoverable with the current data (like a missing external service or Captcha), set `corrected_data` to null.

    Your ONLY output must be a single JSON object. Do NOT include any other prose or markdown, except for the JSON itself.
    
    Example Output (if corrected):
    {{
        "diagnosis": "The error shows 'Invalid Gender' because 'Invalid' is not an accepted option. The previous data was {{...}}.",
        "corrected_data": {{"Email": "{user_data['Email']}", "Country": "{user_data['Country']}", "Gender": "Female"}}
    }}

    Example Output (if uncorrectable):
    {{
        "diagnosis": "The screenshot shows an unsolveable Captcha/reCAPTCHA, requiring human interaction.",
        "corrected_data": null
    }}
    """
    
    content_parts = image_to_parts(screenshot_path, prompt)
    
    response = ADK_CLIENT.models.generate_content(
        model='gemini-2.5-pro', # Use a strong model for reasoning and vision
        contents=content_parts,
        config=types.GenerateContentConfig(
             system_instruction="You are an expert QA engineer. Provide only a single JSON object as requested in the prompt."
        )
    )

    # Clean up the image after analysis
    os.remove(screenshot_path) 
    
    return response.text # Return the raw JSON string for the Agent to process

# The Agent definition (the brain)
RegistrationAgent = Agent(
    name="registration_form_vision_correction_agent",
    model="gemini-2.5-pro", 
    instruction=(
        "You are an expert web automation agent designed for self-correction. "
        "1. Read data using 'read_user_data_from_excel'. "
        "2. For each user, attempt 'register_user_on_web'. "
        "3. **Self-Correction Loop**: If a FAILURE occurs, call 'analyze_screenshot_error' with the `screenshot_path`, original `user_data`, and `message`. "
        "4. **CRITICAL**: If the output from 'analyze_screenshot_error' is valid JSON containing a `corrected_data` object that is NOT null, you MUST immediately call 'register_user_on_web' a second time using the **corrected data**. "
        "5. Keep track of all attempts (initial and corrected) and provide a final consolidated report."
    ),
    tools=[
        register_user_on_web, 
        read_user_data_from_excel, 
        analyze_screenshot_error 
    ]
)
run.py (Execution Script)
The execution script and the user prompt are straightforward. The self-correction logic is entirely handled by the Agent's sophisticated instruction set.

Python

# run.py
# /// script
# --virtualenv
# python=3.11
# dependencies=[
#   "google-adk",
#   "pandas",
#   "openpyxl",
#   "playwright",
#   "python-dotenv"
# ]
# --
import os
from dotenv import load_dotenv
import asyncio
from google.adk.agents.run_config import RunConfig
from google.adk.client import Client
from agent import RegistrationAgent 

load_dotenv()
if "GEMINI_API_KEY" not in os.environ:
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")

# NOTE: This URL is a placeholder and WILL FAIL without a live web form, triggering the self-correction logic.
MOCK_WEB_URL = "https://your-registration-site.com/signup" 

async def main():
    
    # Define the task, emphasizing the self-correction loop
    user_prompt = (
        "Using the 'read_user_data_from_excel' tool, read the data from 'data/users.xlsx'. "
        f"For each user, attempt registration on '{MOCK_WEB_URL}'. "
        "If the initial attempt fails, use 'analyze_screenshot_error' to get a correction. "
        "If a correction is provided, re-attempt the registration with the corrected data. "
        "Finally, provide a consolidated report detailing the initial attempt, the diagnosis, and the final status after correction (if applicable)."
    )
    
    print("--- Running Gemini 2.5 Pro Self-Correcting Vision Agent ---")
    print(f"Target URL: {MOCK_WEB_URL}\n")

    response = await Client().agents.arun(
        agent=RegistrationAgent,
        prompt=user_prompt,
        config=RunConfig(stream=True)
    )

    print("\n--- Final Agent Summary ---")
    print(response.content.text)

if __name__ == "__main__":
    asyncio.run(main())
When you run this code, the agent will:

Attempt to register the user with Gender: Invalid.

The register_user_on_web tool fails and returns a screenshot_path.

The agent calls analyze_screenshot_error, sending the screenshot and data to Gemini 2.5 Pro.

Gemini uses vision to see the error (e.g., "Invalid input for Gender") and returns a structured JSON correction: {"corrected_data": {"Email": "...", "Country": "...", "Gender": "Female"}}.

The agent's instruction compels it to use the new corrected_data and call register_user_on_web again, effectively using the vision tool's output as an immediate callback.
