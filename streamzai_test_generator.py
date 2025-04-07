import os
import argparse
import re
import json
import logging
import datetime
import google.generativeai as genai
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("streamzai_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StreamzAI")

class StreamzAITestGenerator:
    """Main class for generating test cases from project files using AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the test generator.
        
        Args:
            api_key: Google AI API key. If not provided, will try to get from environment variable.
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("No Google API key provided. Please set GOOGLE_API_KEY environment variable or provide it as an argument.")
        else:
            genai.configure(api_key=self.api_key)
        
        # File extensions to analyze
        self.supported_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rb": "ruby",
            ".php": "php"
        }
        
        # Patterns to ignore
        self.ignore_patterns = [
            r"__pycache__",
            r"\.git",
            r"\.vscode",
            r"\.idea",
            r"node_modules",
            r"venv",
            r"env",
            r"dist",
            r"build",
            r"test",
            r"tests"
        ]
    
    def should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored based on ignore patterns.
        
        Args:
            path: Path to check
            
        Returns:
            True if path should be ignored, False otherwise
        """
        for pattern in self.ignore_patterns:
            if re.search(pattern, path):
                return True
        return False
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if a file is supported for test generation.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is supported, False otherwise
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_extensions
    
    def traverse_directory(self, project_path: str) -> List[str]:
        """Traverse a directory and collect all supported files.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            List of file paths that are supported for test generation
        """
        supported_files = []
        
        try:
            for root, dirs, files in os.walk(project_path):
                # Filter out directories that match ignore patterns
                dirs[:] = [d for d in dirs if not self.should_ignore(os.path.join(root, d))]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self.should_ignore(file_path) and self.is_supported_file(file_path):
                        supported_files.append(file_path)
                        logger.debug(f"Found supported file: {file_path}")
        except Exception as e:
            logger.error(f"Error traversing directory {project_path}: {str(e)}")
        
        logger.info(f"Found {len(supported_files)} supported files for test generation")
        return supported_files
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a file to extract information needed for test generation.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing file analysis information
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            ext = os.path.splitext(file_path)[1].lower()
            language = self.supported_extensions.get(ext, "unknown")
            
            return {
                "file_path": file_path,
                "language": language,
                "content": content,
                "size": len(content)
            }
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            return {
                "file_path": file_path,
                "error": str(e)
            }
    
    def generate_test_case(self, file_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate test cases for a file using Google's Generative AI (Gemini).
        
        Args:
            file_analysis: Dictionary containing file analysis information
            
        Returns:
            Dictionary containing generated test cases
        """
        if "error" in file_analysis:
            logger.error(f"Cannot generate test for file with analysis error: {file_analysis['file_path']}")
            return {"error": file_analysis["error"]}
        
        try:
            if not self.api_key:
                return {"error": "No Google API key provided"}
            
            # Prepare prompt for the AI
            language = file_analysis["language"]
            content = file_analysis["content"]
            
            # Truncate content if it's too large
            if len(content) > 30000:  # Gemini has higher token limits than OpenAI
                logger.warning(f"File content too large, truncating: {file_analysis['file_path']}")
                content = content[:30000] + "\n... (content truncated)"
            
            prompt = f"""Generate comprehensive unit tests for the following {language} code. 
            The tests should cover all public functions and methods, including edge cases and error handling.
            For each test, provide a clear description of what is being tested.
            
            CODE TO TEST:
            ```{language}
            {content}
            ```
            
            Generate the test code in the appropriate testing framework for {language}.
            Format the response as valid {language} code that can be directly saved to a file and executed.
            Do not include explanations outside of code comments.
            """
            
            # Configure Gemini model
            model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
            
            # Call Gemini API
            response = model.generate_content(
                [
                    {"role": "user", "parts": [prompt]}
                ],
                generation_config={
                    "temperature": 0.2,  # Lower temperature for more deterministic output
                    "max_output_tokens": 8192
                }
            )
            
            test_content = response.text.strip()
            
            # Extract code from markdown if needed
            if test_content.startswith("```") and test_content.endswith("```"):
                # Extract code between markdown code blocks
                test_content = "\n".join(test_content.split("\n")[1:-1])
            
            return {
                "file_path": file_analysis["file_path"],
                "language": language,
                "test_content": test_content
            }
            
        except Exception as e:
            logger.error(f"Error generating test for {file_analysis['file_path']}: {str(e)}")
            return {
                "file_path": file_analysis["file_path"],
                "error": str(e)
            }
    
    def save_test_case(self, test_case: Dict[str, Any], output_dir: str) -> str:
        """Save a generated test case to a file.
        
        Args:
            test_case: Dictionary containing test case information
            output_dir: Directory to save the test case
            
        Returns:
            Path to the saved test file, or error message
        """
        if "error" in test_case:
            return f"Error: {test_case['error']}"
        
        try:
            # Get original file path and create corresponding test file path
            orig_file_path = test_case["file_path"]
            rel_path = os.path.relpath(orig_file_path, start=os.getcwd())
            
            # Create test file name based on original file
            file_name = os.path.basename(orig_file_path)
            file_base, file_ext = os.path.splitext(file_name)
            
            # Create appropriate test file name based on language
            language = test_case["language"]
            if language == "python":
                test_file_name = f"test_{file_base}{file_ext}"
            else:
                test_file_name = f"{file_base}.test{file_ext}"
            
            # Create directory structure in output directory
            rel_dir = os.path.dirname(rel_path)
            test_dir = os.path.join(output_dir, rel_dir)
            os.makedirs(test_dir, exist_ok=True)
            
            # Save test content to file
            test_file_path = os.path.join(test_dir, test_file_name)
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_case["test_content"])
            
            logger.info(f"Saved test case to {test_file_path}")
            return test_file_path
            
        except Exception as e:
            logger.error(f"Error saving test case for {test_case.get('file_path', 'unknown')}: {str(e)}")
            return f"Error: {str(e)}"
    
    def generate_tests(self, project_path: str, output_dir: str) -> Dict[str, Any]:
        """Generate test cases for all supported files in a project.
        
        Args:
            project_path: Path to the project directory
            output_dir: Directory to save the generated test cases
            
        Returns:
            Dictionary containing summary of test generation
        """
        if not os.path.exists(project_path):
            logger.error(f"Project path does not exist: {project_path}")
            return {"error": f"Project path does not exist: {project_path}"}
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Find all supported files
        logger.info(f"Traversing project directory: {project_path}")
        supported_files = self.traverse_directory(project_path)
        
        # Generate test cases for each file
        results = {
            "total_files": len(supported_files),
            "successful": 0,
            "failed": 0,
            "test_files": []
        }
        
        for file_path in supported_files:
            logger.info(f"Generating test case for: {file_path}")
            
            # Analyze file
            file_analysis = self.analyze_file(file_path)
            
            # Generate test case
            test_case = self.generate_test_case(file_analysis)
            
            # Save test case
            save_result = self.save_test_case(test_case, output_dir)
            
            if isinstance(save_result, str) and save_result.startswith("Error"):
                results["failed"] += 1
                results["test_files"].append({
                    "original_file": file_path,
                    "status": "failed",
                    "error": save_result
                })
            else:
                results["successful"] += 1
                results["test_files"].append({
                    "original_file": file_path,
                    "test_file": save_result,
                    "status": "success"
                })
        
        # Save summary to output directory
        summary_path = os.path.join(output_dir, "test_generation_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Test generation complete. Summary saved to {summary_path}")
        return results


def main():
    """Main entry point for the StreamzAI test generator."""
    parser = argparse.ArgumentParser(description="StreamzAI Test Case Generator")
    parser.add_argument("project_path", help="Path to the project directory")
    parser.add_argument("--output", "-o", default="generated_tests", help="Directory to save generated test cases")
    parser.add_argument("--api-key", help="OpenAI API key (if not set in environment variable)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    generator = StreamzAITestGenerator(api_key=args.api_key)
    results = generator.generate_tests(args.project_path, args.output)
    
    # Print summary
    print("\nTest Generation Summary:")
    print(f"Total files processed: {results['total_files']}")
    print(f"Successful test cases: {results['successful']}")
    print(f"Failed test cases: {results['failed']}")
    print(f"Output directory: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()