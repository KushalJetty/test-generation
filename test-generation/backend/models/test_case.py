from .user import db
from datetime import datetime
import json

class TestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    test_type = db.Column(db.String(64))  # functional, visual, accessibility, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    test_script = db.Column(db.Text)  # JSON or code representation of the test
    is_ai_generated = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=3)  # 1-5 scale, 1 being highest
    selenium_script = db.Column(db.Text)  # Selenium Python code
    recorded_actions = db.Column(db.Text)  # JSON array of recorded actions
    
    # Relationships
    user = db.relationship('User', backref=db.backref('test_cases', lazy=True))
    executions = db.relationship('TestExecution', backref='test_case', lazy=True)
    
    def get_script_as_dict(self):
        if self.test_script:
            return json.loads(self.test_script)
        return {}
    
    def get_recorded_actions(self):
        if self.recorded_actions:
            return json.loads(self.recorded_actions)
        return []
    
    def add_recorded_action(self, action_type, selector=None, value=None, **kwargs):
        """Add a recorded action to the test case"""
        actions = self.get_recorded_actions()
        
        action = {
            'type': action_type,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        if selector:
            action['selector'] = selector
        
        if value:
            action['value'] = value
            
        # Add any additional parameters
        for key, val in kwargs.items():
            action[key] = val
            
        actions.append(action)
        self.recorded_actions = json.dumps(actions)
        return action
    
    def generate_selenium_script(self):
        """Generate a Selenium script from recorded actions"""
        actions = self.get_recorded_actions()
        if not actions:
            return None
            
        # Start building the script
        script_lines = [
            "import unittest",
            "from selenium import webdriver",
            "from selenium.webdriver.chrome.service import Service",
            "from selenium.webdriver.chrome.options import Options",
            "from selenium.webdriver.common.by import By",
            "from selenium.webdriver.support.ui import WebDriverWait",
            "from selenium.webdriver.support import expected_conditions as EC",
            "from webdriver_manager.chrome import ChromeDriverManager",
            "import time",
            "",
            f"class {self.name.replace(' ', '')}Test(unittest.TestCase):",
            "    def setUp(self):",
            "        chrome_options = Options()",
            "        chrome_options.add_argument('--start-maximized')",
            "        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)",
            "        self.wait = WebDriverWait(self.driver, 10)",
            "",
            "    def test_main(self):",
            "        driver = self.driver"
        ]
        
        # Process each action
        for action in actions:
            action_type = action.get('type')
            selector = action.get('selector')
            value = action.get('value')
            
            if action_type == 'navigate':
                script_lines.append(f"        driver.get('{value}')")
                
            elif action_type == 'click':
                script_lines.append(f"        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '{selector}'))).click()")
                
            elif action_type == 'input':
                script_lines.append(f"        element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{selector}')))")
                script_lines.append(f"        element.clear()")
                script_lines.append(f"        element.send_keys('{value}')")
                
            elif action_type == 'select':
                script_lines.append(f"        from selenium.webdriver.support.ui import Select")
                script_lines.append(f"        select = Select(self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{selector}'))))")
                script_lines.append(f"        select.select_by_visible_text('{value}')")
                
            elif action_type == 'wait':
                script_lines.append(f"        time.sleep({value/1000})")  # Convert ms to seconds
                
            elif action_type == 'assert_text':
                script_lines.append(f"        element_text = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{selector}'))).text")
                script_lines.append(f"        self.assertEqual(element_text, '{value}')")
                
            elif action_type == 'assert_element_present':
                script_lines.append(f"        self.assertTrue(self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{selector}'))))")
                
            elif action_type == 'screenshot':
                script_lines.append(f"        driver.save_screenshot('screenshots/{value}.png')")
        
        # Add tearDown method
        script_lines.extend([
            "",
            "    def tearDown(self):",
            "        self.driver.quit()",
            "",
            "if __name__ == '__main__':",
            "    unittest.main()"
        ])
        
        # Join all lines into a single string
        self.selenium_script = "\n".join(script_lines)
        return self.selenium_script
    
    def __repr__(self):
        return f'<TestCase {self.name}>'

class TestExecution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_case.id'))
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(32))  # passed, failed, error, skipped
    browser = db.Column(db.String(32))
    device = db.Column(db.String(64))
    os = db.Column(db.String(64))
    logs = db.Column(db.Text)
    screenshots = db.Column(db.Text)  # JSON array of screenshot paths
    failure_reason = db.Column(db.Text)
    execution_video = db.Column(db.String(255))  # Path to recorded video of test execution
    
    def duration(self):
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def add_screenshot(self, screenshot_path):
        """Add a screenshot to the test execution"""
        screenshots = json.loads(self.screenshots) if self.screenshots else []
        screenshots.append({
            'path': screenshot_path,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.screenshots = json.dumps(screenshots)
        return screenshots
    
    def get_screenshots(self):
        """Get all screenshots for this test execution"""
        if self.screenshots:
            return json.loads(self.screenshots)
        return []
    
    def add_log_entry(self, level, message):
        """Add a log entry to the test execution"""
        logs = json.loads(self.logs) if self.logs else []
        logs.append({
            'level': level,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        })
        self.logs = json.dumps(logs)
        return logs
    
    def get_logs(self):
        """Get all logs for this test execution"""
        if self.logs:
            return json.loads(self.logs)
        return []
    
    def __repr__(self):
        return f'<TestExecution {self.id} for TestCase {self.test_case_id}>'