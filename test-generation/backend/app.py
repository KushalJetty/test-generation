from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sys
import os
import time
import json
import webbrowser
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from flask_caching import Cache

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Import the TestGenerator class
from ai_modules.test_generation.generator import TestGenerator

# Fix the Flask app configuration to properly serve the frontend
app = Flask(__name__, 
           template_folder=os.path.join(project_root, 'templates'), 
           static_folder=os.path.join(project_root, 'static'))
CORS(app)  # Enable CORS for all routes

# Configure caching
cache_config = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300
}
cache = Cache(app, config=cache_config)

# Initialize the test generator
test_generator = TestGenerator()

# Selenium recorder class
class SeleniumRecorder:
    def __init__(self):
        self.driver = None
        self.actions = []
        self.recording = False
        
    def start_recording(self, url):
        try:
            # Enable performance logging
            caps = DesiredCapabilities.CHROME
            caps['goog:loggingPrefs'] = {'performance': 'ALL', 'browser': 'ALL'}
            
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            # Don't use detach option as it can cause issues
            # chrome_options.add_experimental_option("detach", True)
            
            # Add CDP listener for DOM events
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Create the driver with explicit path to ChromeDriver
            driver_path = ChromeDriverManager().install()
            print(f"Using ChromeDriver at: {driver_path}")
            
            self.driver = webdriver.Chrome(
                service=Service(driver_path), 
                options=chrome_options
            )
            
            # Navigate to URL
            print(f"Navigating to URL: {url}")
            self.driver.get(url)
            self.actions = []
            self.add_action("navigate", url=url)
            
            # Inject JavaScript to capture user actions
            print("Injecting recorder script")
            self.inject_recorder_script()
            
            # Open editor window in a separate thread
            threading.Thread(target=self.open_editor_window).start()
            
            self.recording = True
            return True
        except Exception as e:
            print(f"Error starting recording: {str(e)}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            self.recording = False
            raise Exception(f"Failed to start recording: {str(e)}")
    
    def add_action(self, action_type, **kwargs):
        """Add an action to the recorded actions list"""
        action = {'type': action_type, 'timestamp': time.time()}
        action.update(kwargs)
        self.actions.append(action)
        return action
        
    def inject_recorder_script(self):
        """Inject JavaScript to capture user actions"""
        recorder_script = """
        (function() {
            if (window._recorderInjected) return;
            window._recorderInjected = true;
            
            function sendAction(action) {
                console.log('Sending action:', action);
                fetch('http://127.0.0.1:5000/api/record-action', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(action)
                }).catch(err => console.error('Error sending action:', err));
            }
            
            // Click events
            document.addEventListener('click', function(e) {
                const target = e.target;
                const selector = getCssSelector(target);
                
                sendAction({
                    type: 'click',
                    selector: selector,
                    innerText: target.innerText,
                    tagName: target.tagName.toLowerCase()
                });
            }, true);
            
            // Input events - capture both change and input events
            document.addEventListener('change', captureInputEvent, true);
            document.addEventListener('input', captureInputEvent, true);
            
            function captureInputEvent(e) {
                const target = e.target;
                if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
                    const selector = getCssSelector(target);
                    const value = target.value;
                    
                    sendAction({
                        type: 'input',
                        selector: selector,
                        value: value,
                        inputType: target.type || 'text'
                    });
                }
            }
            
            // Helper function to get CSS selector
            function getCssSelector(element) {
                if (element.id) {
                    return '#' + element.id;
                }
                
                if (element.className && typeof element.className === 'string') {
                    const classes = element.className.split(' ').filter(c => c);
                    if (classes.length > 0) {
                        return element.tagName.toLowerCase() + '.' + classes.join('.');
                    }
                }
                
                // Try with attributes
                if (element.hasAttribute('name')) {
                    return element.tagName.toLowerCase() + '[name="' + element.getAttribute('name') + '"]';
                }
                
                // Fallback to position-based selector
                let path = [];
                while (element) {
                    let selector = element.tagName.toLowerCase();
                    let parent = element.parentNode;
                    
                    if (parent) {
                        let siblings = parent.children;
                        if (siblings.length > 1) {
                            let index = Array.prototype.indexOf.call(siblings, element) + 1;
                            selector += ':nth-child(' + index + ')';
                        }
                    }
                    
                    path.unshift(selector);
                    
                    // Stop at body
                    if (element.tagName === 'BODY') break;
                    
                    element = parent;
                }
                
                return path.join(' > ');
            }
            
            console.log('CogniTest recorder injected and running');
        })();
        """
        self.driver.execute_script(recorder_script)
    
    def open_editor_window(self):
        """Open a window to display and edit recorded actions"""
        # Create a simple HTML file for the editor
        editor_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>CogniTest Recorder</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                h1 { margin-top: 0; }
                .action-list { border: 1px solid #ccc; padding: 10px; height: 400px; overflow-y: auto; }
                .action-item { padding: 8px; margin-bottom: 5px; border: 1px solid #eee; cursor: pointer; }
                .action-item:hover { background-color: #f5f5f5; }
                .action-item.selected { background-color: #e0f0ff; }
                .controls { margin-top: 20px; }
                button { padding: 8px 16px; margin-right: 10px; }
                .edit-form { margin-top: 20px; display: none; }
                .edit-form.visible { display: block; }
                .form-group { margin-bottom: 10px; }
                label { display: block; margin-bottom: 5px; }
                input, select { width: 100%; padding: 8px; }
CogniTest/
├── backend/                 # Flask/Django backend
│   ├── api/                 # API endpoints
│   ├── core/                # Core business logic
│   ├── models/              # Database models
│   ├── services/            # Service layer
│   └── utils/               # Utility functions
├── frontend/                # React frontend
├── ai_modules/              # AI components
│   ├── test_generation/     # Test case generation
│   ├── visual_regression/   # Visual testing
│   ├── anomaly_detection/   # Anomaly detection
│   └── predictive_analytics/# Test prioritization
├── automation/              # Test automation integrations
├── deployment/              # Deployment configurations
│   ├── docker/
│   └── kubernetes/
└── docs/                    # Documentation
    └── architecture/        # Architecture diagrams                .copy-btn { position: absolute; top: 10px; right: 10px; padding: 5px 10px; background: #4CAF50; color: white; border: none; cursor: pointer; }
                .copy-btn:hover { background: #45a049; }
                .test-window { position: relative; }
            </style>
        </head>
        <body>
            <h1>CogniTest Recorder</h1>
            <div class="action-list" id="actionList"></div>
            
            <div class="controls">
                <button id="stopBtn">Stop Recording</button>
                <button id="generateSeleniumBtn">Generate Selenium</button>
                <button id="generatePlaywrightBtn">Generate Playwright</button>
                <button id="deleteBtn">Delete Selected</button>
            </div>
            
            <div class="edit-form" id="editForm">
                <h3>Edit Action</h3>
                <div class="form-group">
                    <label for="actionType">Action Type</label>
                    <select id="actionType">
                        <option value="click">Click</option>
                        <option value="input">Input</option>
                        <option value="navigate">Navigate</option>
                        <option value="wait">Wait</option>
                        <option value="assert">Assert</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="actionSelector">Selector</label>
                    <input type="text" id="actionSelector">
                </div>
                <div class="form-group">
                    <label for="actionValue">Value</label>
                    <input type="text" id="actionValue">
                </div>
                <button id="saveActionBtn">Save Changes</button>
                <button id="cancelEditBtn">Cancel</button>
            </div>
            
            <script>
                let actions = [];
                let selectedActionIndex = -1;
                
                // Fetch actions periodically
                function fetchActions() {
                    fetch('/api/get-actions')
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                actions = data.actions;
                                renderActions();
                            }
                        })
                        .catch(err => console.error('Error fetching actions:', err));
                }
                
                // Render action list
                function renderActions() {
                    const actionList = document.getElementById('actionList');
                    actionList.innerHTML = '';
                    
                    actions.forEach((action, index) => {
                        const actionItem = document.createElement('div');
                        actionItem.className = 'action-item' + (index === selectedActionIndex ? ' selected' : '');
                        
                        let actionText = `${index + 1}. ${action.type}`;
                        if (action.selector) actionText += ` - ${action.selector}`;
                        if (action.value) actionText += ` - ${action.value}`;
                        if (action.url) actionText += ` - ${action.url}`;
                        
                        actionItem.textContent = actionText;
                        actionItem.onclick = () => selectAction(index);
                        
                        actionList.appendChild(actionItem);
                    });
                }
                
                // Select an action for editing
                function selectAction(index) {
                    selectedActionIndex = index;
                    renderActions();
                    
                    if (index >= 0) {
                        const action = actions[index];
                        document.getElementById('actionType').value = action.type;
                        document.getElementById('actionSelector').value = action.selector || '';
                        document.getElementById('actionValue').value = action.value || action.url || '';
                        
                        document.getElementById('editForm').className = 'edit-form visible';
                    }
                }
                
                // Save edited action
                document.getElementById('saveActionBtn').onclick = function() {
                    if (selectedActionIndex < 0) return;
                    
                    const type = document.getElementById('actionType').value;
                    const selector = document.getElementById('actionSelector').value;
                    const value = document.getElementById('actionValue').value;
                    
                    fetch('/api/update-action', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            index: selectedActionIndex,
                            action: {
                                type: type,
                                selector: selector,
                                value: value,
                                url: type === 'navigate' ? value : undefined
                            }
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById('editForm').className = 'edit-form';
                            selectedActionIndex = -1;
                            fetchActions();
                        }
                    })
                    .catch(err => console.error('Error updating action:', err));
                };
                
                // Cancel editing
                document.getElementById('cancelEditBtn').onclick = function() {
                    document.getElementById('editForm').className = 'edit-form';
                    selectedActionIndex = -1;
                    renderActions();
                };
                
                // Delete selected action
                document.getElementById('deleteBtn').onclick = function() {
                    if (selectedActionIndex < 0) return;
                    
                    fetch('/api/delete-action', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            index: selectedActionIndex
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            selectedActionIndex = -1;
                            fetchActions();
                        }
                    })
                    .catch(err => console.error('Error deleting action:', err));
                };
                
                // Stop recording
                document.getElementById('stopBtn').onclick = function() {
                    fetch('/api/stop-recording', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('Recording stopped');
                        }
                    })
                    .catch(err => console.error('Error stopping recording:', err));
                };
                
                // Generate Selenium test
                document.getElementById('generateSeleniumBtn').onclick = function() {
                    fetch('/api/generate-selenium-test', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            test_name: 'RecordedTest'
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const testWindow = window.open('', '_blank');
                            testWindow.document.write(`
                                <html>
                                <head>
                                    <title>Generated Selenium Test</title>
                                    <style>
                                        body { font-family: monospace; padding: 20px; }
                                        pre { background-color: #f5f5f5; padding: 15px; border-radius: 5px; position: relative; }
                                        .copy-btn { position: absolute; top: 10px; right: 10px; padding: 5px 10px; background: #4CAF50; color: white; border: none; cursor: pointer; }
                                        .copy-btn:hover { background: #45a049; }
                                    </style>
                                </head>
                                <body>
                                    <h2>Generated Selenium Test</h2>
                                    <div class="test-window">
                                        <button class="copy-btn" onclick="copyToClipboard()">Copy Code</button>
                                        <pre id="codeBlock">${data.test_code}</pre>
                                    </div>
                                    <script>
                                        function copyToClipboard() {
                                            const codeBlock = document.getElementById('codeBlock');
                                            const textArea = document.createElement('textarea');
                                            textArea.value = codeBlock.textContent;
                                            document.body.appendChild(textArea);
                                            textArea.select();
                                            document.execCommand('copy');
                                            document.body.removeChild(textArea);
                                            alert('Code copied to clipboard!');
                                        }
                                    </script>
                                </body>
                                </html>
                            `);
                        }
                    })
                    .catch(err => console.error('Error generating test:', err));
                };
                
                // Generate Playwright test
                document.getElementById('generatePlaywrightBtn').onclick = function() {
                    fetch('/api/generate-playwright-test', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            test_name: 'RecordedTest'
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const testWindow = window.open('', '_blank');
                            testWindow.document.write(`
                                <html>
                                <head>
                                    <title>Generated Playwright Test</title>
                                    <style>
                                        body { font-family: monospace; padding: 20px; }
                                        pre { background-color: #f5f5f5; padding: 15px; border-radius: 5px; position: relative; }
                                        .copy-btn { position: absolute; top: 10px; right: 10px; padding: 5px 10px; background: #4CAF50; color: white; border: none; cursor: pointer; }
                                        .copy-btn:hover { background: #45a049; }
                                    </style>
                                </head>
                                <body>
                                    <h2>Generated Playwright Test</h2>
                                    <div class="test-window">
                                        <button class="copy-btn" onclick="copyToClipboard()">Copy Code</button>
                                        <pre id="codeBlock">${data.test_code}</pre>
                                    </div>
                                    <script>
                                        function copyToClipboard() {
                                            const codeBlock = document.getElementById('codeBlock');
                                            const textArea = document.createElement('textarea');
                                            textArea.value = codeBlock.textContent;
                                            document.body.appendChild(textArea);
                                            textArea.select();
                                            document.execCommand('copy');
                                            document.body.removeChild(textArea);
                                            alert('Code copied to clipboard!');
                                        }
                                    </script>
                                </body>
                                </html>
                            `);
                        }
                    })
                    .catch(err => console.error('Error generating test:', err));
                };
                
                // Start fetching actions
                fetchActions();
                setInterval(fetchActions, 1000);
            </script>
        </body>
        </html>
        """
        
        # Create editor HTML file
        editor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recorder_editor.html')
        with open(editor_path, 'w') as f:
            f.write(editor_html)
            
        # Open the editor in a browser
        webbrowser.open('file://' + editor_path)
    
    def stop_recording(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            
    def generate_selenium_test(self, test_name):
        """Generate a Selenium test from recorded actions"""
        if not self.actions:
            return "No actions recorded"
            
        test_code = f"""import unittest
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from webdriver_manager.chrome import ChromeDriverManager
    import time
    
    class {test_name}(unittest.TestCase):
        def setUp(self):
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            
        def test_main(self):
            driver = self.driver
            wait = self.wait
    """
            
            # Process each action
        for action in self.actions:
                action_type = action.get('type')
                
                if action_type == 'navigate':
                    test_code += f"        driver.get('{action.get('url')}')\n"
                elif action_type == 'click':
                    test_code += f"""        element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '{action.get('selector')}')))
                    element.click()\n"""
                elif action_type == 'input':
                    test_code += f"""        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{action.get('selector')}')))
                    element.clear()
                    element.send_keys('{action.get('value')}')\n"""
                elif action_type == 'keypress':
                    # Handle individual keypresses if needed
                    test_code += f"""        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{action.get('selector')}')))
                    element.send_keys(Keys.{action.get('key').upper() if len(action.get('key')) == 1 else action.get('key')})\n"""
                elif action_type == 'submit':
                    test_code += f"""        form = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{action.get('selector')}')))
                    form.submit()\n"""
                elif action_type == 'wait':
                    test_code += f"        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{action.get('selector')}')))\n"
                elif action_type == 'assert':
                    test_code += f"""        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{action.get('selector')}')))
                    self.assertEqual(element.text, '{action.get('value')}')\n"""
                    
        test_code += """
            def tearDown(self):
                self.driver.quit()
                
            if __name__ == "__main__":
                unittest.main()
            """
        return test_code


# Initialize the recorder
selenium_recorder = SeleniumRecorder()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'CogniTest API',
        'version': '0.1.0'
    })

@app.route('/api/generate-tests', methods=['POST'])
def generate_tests():
    data = request.json
    url = data.get('url')
    test_types = data.get('test_types', ['functional', 'ui'])
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        tests = test_generator.generate_from_url(url, test_types)
        return jsonify(tests)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start-recording', methods=['POST'])
def start_recording():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        success = selenium_recorder.start_recording(url)
        return jsonify({'success': success, 'message': 'Recording started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop-recording', methods=['POST'])
def stop_recording():
    try:
        selenium_recorder.stop_recording()
        return jsonify({'success': True, 'message': 'Recording stopped'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-playwright-test', methods=['POST'])
def generate_playwright_test():
    """API endpoint to generate a Playwright test from recorded actions"""
    data = request.json
    test_name = data.get('test_name', 'AutoGeneratedTest')
    
    try:
        # Generate Playwright test code
        test_code = """
const { test, expect } = require('@playwright/test');

test('""" + test_name + """', async ({ page }) => {
"""
        
        # Process each action
        for action in selenium_recorder.actions:
            action_type = action.get('type')
            
            if action_type == 'navigate':
                test_code += f"  await page.goto('{action.get('url')}');\n"
            elif action_type == 'click':
                test_code += f"  await page.click('{action.get('selector')}');\n"
            elif action_type == 'input':
                test_code += f"  await page.fill('{action.get('selector')}', '{action.get('value')}');\n"
            elif action_type == 'wait':
                test_code += f"  await page.waitForSelector('{action.get('selector')}');\n"
            elif action_type == 'assert':
                test_code += f"  await expect(page.locator('{action.get('selector')}')).toHaveText('{action.get('value')}');\n"
        
        test_code += "});\n"
        
        return jsonify({'success': True, 'test_code': test_code})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/record-action', methods=['POST'])
def record_action():
    """API endpoint to record a user action from the browser"""
    if not selenium_recorder.recording:
        return jsonify({'error': 'Not currently recording'}), 400
        
    try:
        action_data = request.json
        action_type = action_data.get('type')
        
        # Create a new action based on the type
        if action_type == 'click':
            selenium_recorder.add_action(
                'click',
                selector=action_data.get('selector'),
                innerText=action_data.get('innerText'),
                tagName=action_data.get('tagName')
            )
        elif action_type == 'input':
            selenium_recorder.add_action(
                'input',
                selector=action_data.get('selector'),
                value=action_data.get('value'),
                inputType=action_data.get('inputType')
            )
        else:
            # Generic action recording
            selenium_recorder.add_action(action_type, **action_data)
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-actions', methods=['GET'])
def get_actions():
    """API endpoint to get all recorded actions"""
    try:
        return jsonify({
            'success': True,
            'actions': selenium_recorder.actions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-action', methods=['POST'])
def update_action():
    """API endpoint to update a recorded action"""
    try:
        data = request.json
        index = data.get('index')
        action = data.get('action')
        
        if index is None or action is None:
            return jsonify({'error': 'Index and action are required'}), 400
            
        if index < 0 or index >= len(selenium_recorder.actions):
            return jsonify({'error': 'Invalid action index'}), 400
            
        # Update the action
        selenium_recorder.actions[index] = {
            **selenium_recorder.actions[index],  # Keep original data like timestamp
            **action  # Override with new data
        }
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-action', methods=['POST'])
def delete_action():
    """API endpoint to delete a recorded action"""
    try:
        data = request.json
        index = data.get('index')
        
        if index is None:
            return jsonify({'error': 'Index is required'}), 400
            
        if index < 0 or index >= len(selenium_recorder.actions):
            return jsonify({'error': 'Invalid action index'}), 400
            
        # Delete the action
        del selenium_recorder.actions[index]
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-selenium-test', methods=['POST'])
def generate_selenium_test():
    data = request.json
    test_name = data.get('test_name', 'AutoGeneratedTest')
    
    try:
        test_code = selenium_recorder.generate_selenium_test(test_name)
        return jsonify({'success': True, 'test_code': test_code})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add this code at the end of the file to run the Flask server
if __name__ == '__main__':
    print("Starting CogniTest API server...")
    app.run(host='0.0.0.0', port=5000, debug=True)

# Add performance optimizations
from flask_caching import Cache
import threading

# Configure caching
cache_config = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300
}
cache = Cache(app, config=cache_config)

# Use threading for heavy operations
def background_task(func, *args, **kwargs):
    thread = threading.Thread(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

# Add caching to expensive operations
@cache.cached(timeout=60)
def get_cached_actions():
    return recorder.actions if recorder else []

@app.route('/api/get-actions', methods=['GET'])
def get_actions():
    actions = get_cached_actions()
    return jsonify({
        'success': True,
        'actions': actions
    })

# Optimize test generation with background processing
@app.route('/api/generate-selenium-test', methods=['POST'])
def generate_selenium_test():
    data = request.json
    test_name = data.get('test_name', 'RecordedTest')
    
    # Generate test code in the background if it's complex
    if len(recorder.actions) > 20:
        # For complex tests, return immediately and process in background
        response = {
            'success': True,
            'test_code': "// Generating test code, please wait...\n// This may take a few moments for complex tests.",
            'processing': True
        }
        background_task(recorder.generate_selenium_test, test_name)
        return jsonify(response)
    else:
        # For simple tests, generate immediately
        test_code = recorder.generate_selenium_test(test_name)
        return jsonify({
            'success': True,
            'test_code': test_code
        })