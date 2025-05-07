import os
import sys
import json
import tempfile
import re
import subprocess
import argparse

def load_input_values(input_file_path, input_set_name=None):
    """Load input values from the JSON file."""
    try:
        with open(input_file_path, 'r') as f:
            input_data = json.load(f)
        
        # Check if the input data has the expected structure
        if 'test_sets' in input_data and input_set_name:
            for test_set in input_data['test_sets']:
                if test_set['name'] == input_set_name:
                    return test_set['inputs']
            
            # If the specified input set is not found, return None
            print(f"Input set '{input_set_name}' not found in the input file.")
            return None
        
        # For the flat key-value format
        return input_data
    except Exception as e:
        print(f"Error loading input values: {e}")
        return None

def modify_test_file(original_test_path, input_values, headless=False):
    """Create a modified version of the test file with the input values."""
    try:
        with open(original_test_path, 'r') as f:
            test_content = f.read()
        
        # Create a temporary file for the modified test
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp:
            # Add imports if needed
            if 'import os' not in test_content:
                test_content = "import os\n" + test_content
            
            # Replace the headless option if specified
            if headless:
                test_content = re.sub(
                    r'browser = await p\.chromium\.launch\(headless=False\)',
                    'browser = await p.chromium.launch(headless=True)',
                    test_content
                )
            
            # Replace input values
            for selector, value in input_values.items():
                if value is None:
                    continue
                
                # Find all fill operations for this selector
                fill_pattern = rf"await page\.fill\('{selector}', '([^']+)'\)"
                matches = re.findall(fill_pattern, test_content)
                
                if matches:
                    # Replace the last fill operation with our value
                    last_value = matches[-1]
                    test_content = test_content.replace(
                        f"await page.fill('{selector}', '{last_value}')",
                        f"await page.fill('{selector}', '{value}')"
                    )
            
            # Write the modified test content to the temporary file
            temp.write(test_content)
            return temp.name
    except Exception as e:
        print(f"Error modifying test file: {e}")
        return None

def run_test(test_path):
    """Run the test file using Python."""
    try:
        result = subprocess.run(
            [sys.executable, test_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Test execution timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"Error running test: {e}")
        return False

def cleanup(temp_file_path):
    """Clean up temporary files."""
    try:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
    except Exception as e:
        print(f"Error cleaning up temporary file: {e}")

def main():
    parser = argparse.ArgumentParser(description='Run a test with custom input values')
    parser.add_argument('--test', required=True, help='Path to the test file')
    parser.add_argument('--input', required=True, help='Path to the input values JSON file')
    parser.add_argument('--set', help='Name of the input set to use')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    # Load input values
    input_values = load_input_values(args.input, args.set)
    if not input_values:
        print("Failed to load input values. Exiting.")
        return 1
    
    # Modify the test file
    temp_test_path = modify_test_file(args.test, input_values, args.headless)
    if not temp_test_path:
        print("Failed to modify test file. Exiting.")
        return 1
    
    try:
        # Run the modified test
        success = run_test(temp_test_path)
        return 0 if success else 1
    finally:
        # Clean up
        cleanup(temp_test_path)

if __name__ == "__main__":
    sys.exit(main())
