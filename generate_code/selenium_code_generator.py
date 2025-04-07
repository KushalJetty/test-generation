import json
from datetime import datetime

class SeleniumCodeGenerator:
    def __init__(self):
        self.indent = "    "
        self.imports = [
            "import unittest",
            "from selenium import webdriver",
            "from selenium.webdriver.common.by import By",
            "from selenium.webdriver.support.ui import WebDriverWait",
            "from selenium.webdriver.support import expected_conditions as EC",
            "from selenium.webdriver.common.keys import Keys",
            "import time"
        ]

    def generate_code(self, actions):
        """Generate Selenium code from recorded actions."""
        code = []
        
        # Add imports
        code.extend(self.imports)
        code.append("")
        
        # Add test class
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        code.extend([
            f"class TestRecorded_{timestamp}(unittest.TestCase):",
            "",
            f"{self.indent}def setUp(self):",
            f"{self.indent*2}# Initialize Chrome driver",
            f"{self.indent*2}chrome_options = webdriver.ChromeOptions()",
            f"{self.indent*2}chrome_options.add_argument('--start-maximized')",
            f"{self.indent*2}self.driver = webdriver.Chrome(options=chrome_options)",
            f"{self.indent*2}self.wait = WebDriverWait(self.driver, 10)",
            ""
        ])
        
        # Add test method
        code.extend([
            f"{self.indent}def test_recorded_actions(self):",
            f"{self.indent*2}try:",
            f"{self.indent*3}# Navigate to the initial URL",
            f"{self.indent*3}self.driver.get('https://test.teamstreamz.com/')",
            f"{self.indent*3}time.sleep(2)  # Wait for page to load",
            ""
        ])
        
        # Add recorded actions
        if actions and len(actions) > 0:
            for action in actions:
                code.extend(self._generate_action_code(action))
        else:
            code.extend([
                f"{self.indent*3}# No actions were recorded",
                f"{self.indent*3}print('No actions were recorded during the test session.')",
                ""
            ])
        
        # Add cleanup
        code.extend([
            "",
            f"{self.indent*2}finally:",
            f"{self.indent*3}# Close the browser",
            f"{self.indent*3}self.driver.quit()",
            "",
            f"{self.indent}def tearDown(self):",
            f"{self.indent*2}if hasattr(self, 'driver'):",
            f"{self.indent*3}self.driver.quit()",
            "",
            "if __name__ == '__main__':",
            f"{self.indent}unittest.main()"
        ])
        
        return "\n".join(code)

    def _generate_action_code(self, action):
        """Generate code for a single action."""
        code = []
        action_type = action.get('type')
        
        if action_type == 'click':
            code.extend([
                f"{self.indent*3}# Click on element {action['selector']}",
                f"{self.indent*3}element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '{action['selector']}')))",
                f"{self.indent*3}element.click()",
                f"{self.indent*3}time.sleep(1)  # Wait for action to complete"
            ])
        
        elif action_type == 'input':
            code.extend([
                f"{self.indent*3}# Input text into {action['selector']}",
                f"{self.indent*3}element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{action['selector']}')))",
                f"{self.indent*3}element.clear()",
                f"{self.indent*3}element.send_keys('{action['value']}')",
                f"{self.indent*3}time.sleep(0.5)  # Wait for typing to complete"
            ])
        
        elif action_type == 'submit':
            code.extend([
                f"{self.indent*3}# Submit form {action['selector']}",
                f"{self.indent*3}form = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{action['selector']}')))",
                f"{self.indent*3}form.submit()",
                f"{self.indent*3}time.sleep(2)  # Wait for form submission"
            ])
        
        elif action_type == 'keypress':
            code.extend([
                f"{self.indent*3}# Press {action['key']} key",
                f"{self.indent*3}active_element = self.driver.switch_to.active_element",
                f"{self.indent*3}active_element.send_keys(Keys.{action['key'].upper()})",
                f"{self.indent*3}time.sleep(0.5)  # Wait for key press"
            ])
        
        elif action_type == 'navigate':
            code.extend([
                f"{self.indent*3}# Navigate to {action['url']}",
                f"{self.indent*3}self.driver.get('{action['url']}')",
                f"{self.indent*3}time.sleep(2)  # Wait for navigation"
            ])
        
        elif action_type == 'dom_change':
            code.extend([
                f"{self.indent*3}# Wait for DOM changes to complete",
                f"{self.indent*3}time.sleep(1)  # Wait for page to stabilize"
            ])
        
        return code

def generate_test_file(actions, output_dir="generated_tests"):
    """Generate a test file from recorded actions."""
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate the code
    generator = SeleniumCodeGenerator()
    code = generator.generate_code(actions)
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"test_recorded_{timestamp}.py")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)
    
    return filename 