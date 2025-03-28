#!/usr/bin/env python

import os
import sys
import json
import argparse
import logging
from test_runner import StreamzAITestRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("django_test_runner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Django-TestRunner")

def main():
    parser = argparse.ArgumentParser(description="Run Django tests from test_generation_summary.json")
    parser.add_argument("--summary-file", default="generated_tests/test_generation_summary.json", 
                        help="Path to the test generation summary JSON file")
    parser.add_argument("--django-project-path", required=True,
                        help="Path to the Django project root directory")
    parser.add_argument("--output", help="Output file for test results (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Check if the Django project path exists
    if not os.path.exists(args.django_project_path):
        logger.error(f"Django project path does not exist: {args.django_project_path}")
        return 1
    
    # Check if manage.py exists in the Django project path
    manage_py_path = os.path.join(args.django_project_path, "manage.py")
    if not os.path.exists(manage_py_path):
        logger.error(f"manage.py not found in Django project path: {manage_py_path}")
        return 1
    
    # Load test files from summary file
    if not os.path.exists(args.summary_file):
        logger.error(f"Test summary file not found: {args.summary_file}")
        return 1
    
    try:
        with open(args.summary_file, 'r') as f:
            summary = json.load(f)
            test_files = [item['test_file'] for item in summary.get('test_files', [])]
            logger.info(f"Loaded {len(test_files)} test files from summary file")
    except Exception as e:
        logger.error(f"Error loading test summary file: {str(e)}")
        return 1
    
    # Initialize the test runner
    runner = StreamzAITestRunner(
        test_files=test_files,
        is_django=True,
        django_project_path=args.django_project_path
    )
    
    # Run the tests
    logger.info(f"Running {len(test_files)} Django tests...")
    results = runner.run_tests()
    
    # Print summary
    summary = results["summary"]
    print("\nTest Run Summary:")
    print(f"Status: {results['status']}")
    print(f"Total files: {summary['total_files']}")
    print(f"Passed files: {summary['passed_files']}")
    print(f"Failed files: {summary['failed_files']}")
    print(f"Error files: {summary['error_files']}")
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed tests: {summary['passed_tests']}")
    print(f"Failed tests: {summary['failed_tests']}")
    print(f"Error tests: {summary['error_tests']}")
    print(f"Skipped tests: {summary['skipped_tests']}")
    print(f"Execution time: {summary['execution_time']:.2f} seconds")
    
    # Save results to file if specified
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Test results saved to {args.output}")
        except Exception as e:
            logger.error(f"Error saving test results: {str(e)}")
    
    # Return exit code based on test status
    if results["status"] == "error":
        return 2
    elif results["status"] == "failed":
        return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())