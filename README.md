# StreamzAI Test Case Generator - Internship project

StreamzAI Test Case Generator is a powerful web application that generates test cases for your project files using Plawright Chromium Window. It provides a user-friendly interface to manage projects, test suites, and test runs, with comprehensive reporting and visualization features.

## Features

- Web-based dashboard for managing test generation
- Automatic traversal of project directories
- Support for multiple programming languages (Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Ruby, PHP)
- AI-powered test case generation using Google's Generative AI
- Test execution and result tracking
- Visual reporting with charts and statistics
- Export capabilities for test results
- Structured output format that mirrors your project structure

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```
After installing all the dependencies install playwright chrome engines if you face any errors else not required to run the below command
```bash
playwright install
```

## Environment Setup

This application is configured on python version 3.12.7
create virtual environment using conda
```bash
# On Windows
conda create -p venv python == 3.12.7

```
```bash
# Activate venv using
conda activate venv/
```



## Running the Application

1. Initialize the database (first time only):

```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

2. Start the Flask server:

```bash
python app.py
```

3. Open your web browser and navigate to `http://localhost:5000`

## Using the Application

### Dashboard

The dashboard provides an overview of your projects, test suites, test runs, and recent activity. From here, you can navigate to different sections of the application.

### Projects

1. Create a new project by clicking "Add Project"
2. Provide a name, path to your project directory, and optional description
3. Submit to create the project

### Test Suites

1. Create a new test suite by clicking "Add Test Suite"
2. Select a project, provide a name and optional description
3. Submit to create the test suite
4. The application will scan your project directory and generate test cases for supported files

### Test Runs

1. Create a new test run by clicking "Add Test Run"
2. Select a test suite, provide a name
3. Submit to start the test run
4. The application will execute the generated test cases and record the results

### Reports

The reports section provides visualizations and statistics about your test runs, including:
- Test result distribution
- Pass/fail rates
- Execution times
- Detailed test case information

You can also export test results to various formats for further analysis.


## Supported File Extensions

- Python (.py)

## Example Output

```bash
from playwright.async_api import async_playwright
import asyncio

async def test_recorded_actions():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://www.wikipedia.org')
        await page.click('main > nav:nth-of-type(1) > div:nth-of-type(1) > a > strong')
        await page.click('.cdx-button.cdx-button--action-default.cdx-button--weight-normal.cdx-button--size-medium.cdx-button--framed.cdx-search-input__end-button')
        await browser.close()
asyncio.run(test_recorded_actions())
```

## License

MIT
