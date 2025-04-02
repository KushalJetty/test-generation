# StreamzAI Test Case Generator

StreamzAI Test Case Generator is a powerful web application that automatically generates test cases for your project files using Google's Generative AI. It provides a user-friendly interface to manage projects, test suites, and test runs, with comprehensive reporting and visualization features.

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

## Environment Setup

This application requires a Google AI API key to generate test cases. You can set it as an environment variable:

```bash
# On Windows
set GOOGLE_API_KEY=your_google_api_key

# On macOS/Linux
export GOOGLE_API_KEY=your_google_api_key
```

Alternatively, you can provide it directly when running the application.

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

## Command Line Usage

In addition to the web interface, you can also use the command-line tool to generate test cases:

```bash
python streamzai_test_generator.py /path/to/your/project --api-key your_google_api_key
```

### Command Line Arguments

- `project_path`: Path to the project directory (required)
- `--api-key`: Google AI API key (if not set in environment variable)
- `--verbose`, `-v`: Enable verbose logging

## Supported File Extensions

- Python (.py)
- JavaScript (.js)
- TypeScript (.ts)
- Java (.java)
- C (.c)
- C++ (.cpp)
- C# (.cs)
- Go (.go)
- Ruby (.rb)
- PHP (.php)

## Example Output

The generator creates test files that mirror your project structure, along with a summary file containing information about the test generation process.

## License

MIT