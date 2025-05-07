# Test Runner App

A standalone Flask application for running Playwright test files with a simple web interface.

## Features

- Simple web interface with a single "Run Test" button
- Popup window with test configuration options:
  - File picker to select test files
  - Input mode selection (default, dynamic, or existing custom inputs)
  - Headless mode toggle
- Support for running tests with different input configurations
- Display of test execution results and errors

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:

```bash
python -m playwright install
```

## Usage

1. Start the Flask application:

```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`

3. Click the "Run Test" button to open the configuration popup

4. In the popup:
   - Select a test file to run
   - Choose an input mode:
     - Default input: Uses the default values in the test
     - Dynamic custom input: Allows for dynamic input during test execution
     - Existing custom input: Upload a JSON file with input values and select an input set
   - When selecting "Existing custom input":
     - Upload a JSON file with input values (similar to `tests/input_values.json`)
     - Select an input set from the dropdown (populated based on the uploaded file)
   - Toggle headless mode if needed
   - Click "Run Test" to execute the test

## File Structure

```
test_runner_app/
├── app.py                # Main Flask application
├── static/               # Static files
│   └── style.css         # CSS for the web interface
├── templates/            # HTML templates
│   └── index.html        # Main page with the "Run Test" button
├── tests/                # Test files directory
│   └── test_case.py      # Sample test file
└── requirements.txt      # Dependencies
```

## Creating Test Files

Test files should be written using Playwright's async API. Here's a basic template:

```python
from playwright.async_api import async_playwright
import asyncio
import os
import json

async def get_input_values():
    """Get input values based on the environment configuration."""
    # Check if we have a test input file specified
    input_file = os.environ.get('TEST_INPUT_FILE')
    if input_file and os.path.exists(input_file):
        try:
            with open(input_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading input file: {e}")

    # Default values if no input file is specified
    return {
        "username": "default_user",
        "password": "default_password"
    }

async def test_recorded_actions():
    # Get input values
    input_values = await get_input_values()

    # Determine if we should run in headless mode
    headless = os.environ.get('PLAYWRIGHT_HEADLESS', 'false').lower() == 'true'

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto('https://example.com')

        # Use input values in your test
        if 'username' in input_values:
            await page.fill('#username', input_values['username'])

        # Add your test steps here
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_recorded_actions())
```

## Input Values JSON Format

The application supports two formats for input values JSON files:

### Format 1: Test Sets Array

```json
{
  "test_sets": [
    {
      "name": "Default Login",
      "inputs": {
        "username": "test_user",
        "password": "test_password"
      }
    },
    {
      "name": "Admin Login",
      "inputs": {
        "username": "admin",
        "password": "admin123"
      }
    }
  ]
}
```

### Format 2: Flat Key-Value Pairs

```json
{
  "#Username": "test_user",
  "#Password": "test_password",
  ".form-control": "some_value"
}
```
