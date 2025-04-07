import os
import subprocess
import json
import time
from datetime import datetime

class SeleniumRunner:
    def __init__(self, test_dir):
        self.test_dir = test_dir
        self.results = {}
        
    def run_test(self, test_file):
        """Run a single Selenium test file"""
        start_time = time.time()
        test_path = os.path.join(self.test_dir, test_file)
        
        if not os.path.exists(test_path):
            raise FileNotFoundError(f"Test file not found: {test_path}")
            
        try:
            # Run the test using Python
            result = subprocess.run(
                ['python', test_path],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Parse the output
            success = result.returncode == 0
            output = result.stdout
            error = result.stderr
            
            # Store the result
            test_result = {
                'test_file': test_file,
                'success': success,
                'execution_time': execution_time,
                'output': output,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
            
            self.results[test_file] = test_result
            return test_result
            
        except Exception as e:
            # Handle any exceptions
            test_result = {
                'test_file': test_file,
                'success': False,
                'execution_time': time.time() - start_time,
                'output': '',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            self.results[test_file] = test_result
            return test_result
            
    def run_all_tests(self):
        """Run all Selenium tests in the test directory"""
        results = []
        
        # Get all Python files in the test directory
        test_files = [f for f in os.listdir(self.test_dir) if f.endswith('.py')]
        
        for test_file in test_files:
            result = self.run_test(test_file)
            results.append(result)
            
        return results
        
    def save_results(self, output_file):
        """Save test results to a JSON file"""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
            
    def load_results(self, input_file):
        """Load test results from a JSON file"""
        with open(input_file, 'r') as f:
            self.results = json.load(f)