from flask import render_template, request, jsonify, Response, session, send_from_directory, Blueprint
import os
from playwright.async_api import async_playwright
import asyncio
import threading
import queue
import json
import time
import pandas as pd
import ast
from .test_execution.optimizer import TestOptimizer
from .test_execution.vpn_manager import VPNManager
from .test_execution.reporter import TestReporter, generate_report
from . import test_runner_bp
from playwright.sync_api import sync_playwright

# Global queues for execution and events
execution_queue = queue.Queue()
event_queue = queue.Queue(maxsize=1000)
scheduled_tests = {}

# Global state for test execution
execution_state = {
    'running': False,
    'reporter': None,
    'event_queue': queue.Queue(),
    'current_step': 0,
    'stats': {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'retried': 0
    }
}

class AsyncExecutor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = None
        self.pending_inputs = {}
        self.stop_requested = False

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.execute_tests())
        self.loop.close()

    async def execute_tests(self):
        while True:
            test_config = execution_queue.get()
            # Reset stop flag for new test
            self.stop_requested = False
            try:
                event_queue.put({'type': 'status', 'data': 'Starting test execution'})
                async with async_playwright() as p:
                    await self._run_test(p, test_config)
            except Exception as e:
                event_queue.put({'type': 'error', 'data': str(e)})
            finally:
                execution_queue.task_done()
                if self.stop_requested:
                    event_queue.put({'type': 'status', 'data': 'Test execution stopped by user'})
                else:
                    event_queue.put({'type': 'status', 'data': 'Test execution completed'})

    async def _run_test(self, playwright, config):
        # Initialize test components
        optimizer = TestOptimizer(config.get('mode', 'default'), config.get('inputs'))
        reporter = TestReporter()

        # Launch browser
        browser_type = config.get('browser', 'chromium')
        browser = await getattr(playwright, browser_type).launch(headless=config.get('headless', False))
        context = await browser.new_context()
        page = await context.new_page()

        # Setup network and console logging
        page.on("console", lambda msg: event_queue.put({
            'type': 'console',
            'data': {'type': msg.type, 'text': msg.text}
        }))

        page.on("request", lambda request: reporter.record_network_request(request))
        page.on("response", lambda response: reporter.record_network_response(response))

        # VPN Connection if configured
        vpn_active = False
        if config.get('vpn_config'):
            try:
                with VPNManager(config['vpn_config']) as vpn:
                    vpn_active = await vpn.connect()
                    if vpn_active:
                        event_queue.put({'type': 'status', 'data': f"Connected to VPN: {config['vpn_config']}"})
            except Exception as e:
                event_queue.put({'type': 'error', 'data': f"VPN connection failed: {str(e)}"})

        # Execute test steps
        try:
            # Navigate to initial URL if provided
            if config.get('url'):
                await page.goto(config['url'])

            # Process and execute test steps
            if config.get('test_steps'):
                steps = optimizer.process_steps(config['test_steps'])

                for i, step in enumerate(steps):
                    # Check if stop was requested
                    if self.stop_requested:
                        event_queue.put({'type': 'status', 'data': 'Stopping test execution...'})
                        break
                    
                    # Execute the step
                    await self._execute_step(page, step, config.get('retries', 3), optimizer)
                    
                    # Check if we should stop on failure
                    if config.get('stopOnFailure', False) and reporter.has_failures():
                        event_queue.put({'type': 'status', 'data': 'Stopping on failure as configured'})
                        break
                    
                    # Add a small delay between steps
                    await asyncio.sleep(0.5)
            
            # Generate and save report
            report_path = generate_report(reporter, config.get('report_format', 'json'))
            event_queue.put({'type': 'report', 'data': report_path})
            
        except Exception as e:
            event_queue.put({'type': 'error', 'data': f"Test execution error: {str(e)}"})
        finally:
            # Close VPN if active
            if vpn_active:
                try:
                    with VPNManager(config['vpn_config']) as vpn:
                        await vpn.disconnect()
                        event_queue.put({'type': 'status', 'data': "Disconnected from VPN"})
                except Exception as e:
                    event_queue.put({'type': 'error', 'data': f"VPN disconnection error: {str(e)}"})
            
            # Close browser
            await browser.close()

    async def _execute_step(self, page, step, max_retries=3, optimizer=None):
        action = step.get('action', '').lower()
        selector = step.get('selector', '')
        value = step.get('value', '')
        
        # Skip empty steps
        if not action:
            return
        
        # Log the step
        event_queue.put({'type': 'step', 'data': step})
        
        # Handle different action types
        if action == 'click':
            await self._handle_click(page, selector, max_retries)
        elif action in ['fill', 'type', 'input']:
            await self._handle_input(page, selector, value, max_retries, optimizer)
        elif action == 'select':
            await self._handle_select(page, selector, value, max_retries)
        elif action == 'check':
            await self._handle_check(page, selector, max_retries)
        elif action == 'uncheck':
            await self._handle_uncheck(page, selector, max_retries)
        elif action == 'wait':
            await self._handle_wait(page, value)
        elif action == 'screenshot':
            await self._handle_screenshot(page, value)
        elif action == 'navigate':
            await self._handle_navigate(page, value)
        else:
            event_queue.put({'type': 'warning', 'data': f"Unknown action: {action}"})
    
    async def _handle_click(self, page, selector, max_retries):
        for attempt in range(max_retries):
            try:
                await page.click(selector)
                event_queue.put({'type': 'success', 'data': f"Clicked {selector}"})
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    event_queue.put({'type': 'warning', 'data': f"Click attempt {attempt+1} failed: {str(e)}"})
                    await asyncio.sleep(1)
                else:
                    event_queue.put({'type': 'error', 'data': f"Failed to click {selector}: {str(e)}"})
                    raise
    
    async def _handle_input(self, page, selector, value, max_retries, optimizer):
        # Check if this is a dynamic input that needs user interaction
        if value.startswith('{') and value.endswith('}'):
            var_name = value[1:-1]
            if optimizer and var_name in optimizer.input_values:
                value = optimizer.input_values[var_name]
            else:
                # Wait for user input
                future = asyncio.Future()
                self.pending_inputs[var_name] = future
                event_queue.put({'type': 'input_required', 'data': var_name})
                value = await future
                del self.pending_inputs[var_name]
        
        for attempt in range(max_retries):
            try:
                await page.fill(selector, value)
                event_queue.put({'type': 'success', 'data': f"Filled {selector} with value"})
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    event_queue.put({'type': 'warning', 'data': f"Fill attempt {attempt+1} failed: {str(e)}"})
                    await asyncio.sleep(1)
                else:
                    event_queue.put({'type': 'error', 'data': f"Failed to fill {selector}: {str(e)}"})
                    raise
    
    async def _handle_select(self, page, selector, value, max_retries):
        for attempt in range(max_retries):
            try:
                await page.select_option(selector, value)
                event_queue.put({'type': 'success', 'data': f"Selected {value} in {selector}"})
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    event_queue.put({'type': 'warning', 'data': f"Select attempt {attempt+1} failed: {str(e)}"})
                    await asyncio.sleep(1)
                else:
                    event_queue.put({'type': 'error', 'data': f"Failed to select {value} in {selector}: {str(e)}"})
                    raise
    
    async def _handle_check(self, page, selector, max_retries):
        for attempt in range(max_retries):
            try:
                await page.check(selector)
                event_queue.put({'type': 'success', 'data': f"Checked {selector}"})
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    event_queue.put({'type': 'warning', 'data': f"Check attempt {attempt+1} failed: {str(e)}"})
                    await asyncio.sleep(1)
                else:
                    event_queue.put({'type': 'error', 'data': f"Failed to check {selector}: {str(e)}"})
                    raise
    
    async def _handle_uncheck(self, page, selector, max_retries):
        for attempt in range(max_retries):
            try:
                await page.uncheck(selector)
                event_queue.put({'type': 'success', 'data': f"Unchecked {selector}"})
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    event_queue.put({'type': 'warning', 'data': f"Uncheck attempt {attempt+1} failed: {str(e)}"})
                    await asyncio.sleep(1)
                else:
                    event_queue.put({'type': 'error', 'data': f"Failed to uncheck {selector}: {str(e)}"})
                    raise
    
    async def _handle_wait(self, page, value):
        try:
            wait_time = int(value) if value else 1000
            await page.wait_for_timeout(wait_time)
            event_queue.put({'type': 'success', 'data': f"Waited for {wait_time}ms"})
        except Exception as e:
            event_queue.put({'type': 'error', 'data': f"Wait failed: {str(e)}"})
    
    async def _handle_screenshot(self, page, filename):
        try:
            if not filename:
                filename = f"screenshot_{int(time.time())}.png"
            
            # Ensure screenshots directory exists
            os.makedirs(os.path.join('test_runner', 'screenshots'), exist_ok=True)
            
            # Take screenshot
            screenshot_path = os.path.join('test_runner', 'screenshots', filename)
            await page.screenshot(path=screenshot_path)
            event_queue.put({'type': 'success', 'data': f"Screenshot saved to {screenshot_path}"})
        except Exception as e:
            event_queue.put({'type': 'error', 'data': f"Screenshot failed: {str(e)}"})
    
    async def _handle_navigate(self, page, url):
        try:
            await page.goto(url)
            event_queue.put({'type': 'success', 'data': f"Navigated to {url}"})
        except Exception as e:
            event_queue.put({'type': 'error', 'data': f"Navigation failed: {str(e)}"})
            raise

# Start the executor thread
executor = AsyncExecutor()
executor.start()

test_runner = Blueprint('test_runner', __name__)

@test_runner.route('/')
def home():
    return render_template('test_runner/index.html')

@test_runner.route('/upload-test', methods=['POST'])
def upload_test():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and file.filename.endswith('.json'):
        # Save the uploaded file
        upload_dir = os.path.join('test_runner', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)
        
        # Load the test configuration
        try:
            with open(file_path, 'r') as f:
                test_config = json.load(f)
            
            # Extract URL from steps if not provided
            if not test_config.get('url') and test_config.get('test_steps'):
                url = extract_url_from_steps(test_config['test_steps'])
                if url:
                    test_config['url'] = url
            
            return jsonify({'success': True, 'config': test_config})
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON file'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif file and file.filename.endswith('.py'):
        # Save the uploaded file
        upload_dir = os.path.join('test_runner', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)
        
        # Extract steps from Python file
        try:
            steps = extract_steps_from_python(file_path)
            return jsonify({'success': True, 'steps': steps})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Unsupported file type'}), 400

def extract_url_from_steps(steps):
    for step in steps:
        if step.get('action') == 'navigate' and step.get('value'):
            return step['value']
    return None

def extract_steps_from_python(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Parse the Python file
    tree = ast.parse(content)
    
    # Extract steps from the AST
    steps = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Look for page.goto, page.click, page.fill, etc.
            if isinstance(node.func, ast.Attribute):
                if node.func.value.id == 'page':
                    action = node.func.attr
                    if action in ['goto', 'click', 'fill', 'type', 'select_option', 'check', 'uncheck']:
                        step = {'action': action}
                        
                        # Extract arguments
                        if node.args:
                            if action == 'goto':
                                step['value'] = extract_string_value(node.args[0])
                            elif action in ['click', 'check', 'uncheck']:
                                step['selector'] = extract_string_value(node.args[0])
                            elif action in ['fill', 'type']:
                                step['selector'] = extract_string_value(node.args[0])
                                if len(node.args) > 1:
                                    step['value'] = extract_string_value(node.args[1])
                            elif action == 'select_option':
                                step['selector'] = extract_string_value(node.args[0])
                                if len(node.args) > 1:
                                    step['value'] = extract_string_value(node.args[1])
                        
                        steps.append(step)
    
    return steps

def extract_string_value(node):
    if isinstance(node, ast.Str):
        return node.s
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None

@test_runner.route('/run-test', methods=['POST'])
def run_test():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Add test to execution queue
        execution_queue.put(data)
        
        return jsonify({'success': True, 'message': 'Test added to execution queue'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@test_runner.route('/get-input-fields', methods=['POST'])
def get_input_fields():
    try:
        data = request.get_json()
        if not data or 'steps' not in data:
            return jsonify({'error': 'No steps provided'}), 400
        
        # Extract input fields from steps
        input_fields = []
        for step in data['steps']:
            if step.get('action') in ['fill', 'type', 'input'] and step.get('value', '').startswith('{') and step.get('value', '').endswith('}'):
                var_name = step['value'][1:-1]
                input_fields.append({
                    'name': var_name,
                    'selector': step['selector']
                })
        
        return jsonify({'input_fields': input_fields})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@test_runner.route('/set-input-value', methods=['POST'])
def set_input_value():
    try:
        data = request.get_json()
        if not data or 'var_name' not in data or 'value' not in data:
            return jsonify({'error': 'Missing var_name or value'}), 400
        
        var_name = data['var_name']
        value = data['value']
        
        # Set the input value in the pending inputs
        if var_name in executor.pending_inputs:
            future = executor.pending_inputs[var_name]
            asyncio.run_coroutine_threadsafe(_set_future_result(future, value), executor.loop)
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'No pending input for {var_name}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

async def _set_future_result(future, result):
    future.set_result(result)

@test_runner.route('/schedule-test', methods=['POST'])
def schedule_test():
    try:
        data = request.get_json()
        if not data or 'config' not in data or 'schedule' not in data:
            return jsonify({'error': 'Missing config or schedule'}), 400
        
        test_id = str(int(time.time()))
        scheduled_tests[test_id] = {
            'config': data['config'],
            'schedule': data['schedule'],
            'status': 'scheduled'
        }
        
        return jsonify({'success': True, 'test_id': test_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@test_runner.route('/cancel-test', methods=['POST'])
def cancel_test():
    try:
        data = request.get_json()
        if not data or 'test_id' not in data:
            return jsonify({'error': 'Missing test_id'}), 400
        
        test_id = data['test_id']
        if test_id in scheduled_tests:
            scheduled_tests[test_id]['status'] = 'cancelled'
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'Test {test_id} not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@test_runner.route('/execute', methods=['POST'])
def execute_test():
    """Start test execution."""
    if execution_state['running']:
        return jsonify({'error': 'Test already running'}), 400

    execution_state['running'] = True
    execution_state['reporter'] = TestReporter()
    execution_state['current_step'] = 0
    execution_state['stats'] = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'retried': 0
    }

    # Start test execution in a new thread
    import threading
    thread = threading.Thread(target=run_test)
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Test execution started'})

@test_runner.route('/stop', methods=['POST'])
def stop_test():
    """Stop test execution."""
    execution_state['running'] = False
    return jsonify({'message': 'Test execution stopped'})

@test_runner.route('/events')
def event_stream():
    """SSE endpoint for real-time updates."""
    def generate():
        while True:
            try:
                event = execution_state['event_queue'].get(timeout=1)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                if not execution_state['running']:
                    break
                continue
    
    return Response(generate(), mimetype='text/event-stream')

@test_runner.route('/report')
def view_report():
    """Generate and view test report."""
    if execution_state['reporter']:
        report_path = generate_report(execution_state['reporter'], 'html')
        return jsonify({'report_url': report_path})
    return jsonify({'error': 'No test report available'}), 404

def run_test():
    """Execute the test case."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            reporter = execution_state['reporter']

            # Example test steps (replace with your actual test steps)
            test_steps = [
                {'action': 'navigate', 'value': 'https://example.com'},
                {'action': 'click', 'selector': '#login-button'},
                {'action': 'fill', 'selector': '#username', 'value': 'testuser'},
                {'action': 'fill', 'selector': '#password', 'value': 'password123'},
                {'action': 'click', 'selector': '#submit-button'}
            ]

            for step in test_steps:
                if not execution_state['running']:
                    break

                try:
                    start_time = time.time()
                    
                    # Execute step
                    if step['action'] == 'navigate':
                        page.goto(step['value'])
                        status = 'passed'
                    elif step['action'] == 'click':
                        page.click(step['selector'])
                        status = 'passed'
                    elif step['action'] == 'fill':
                        page.fill(step['selector'], step['value'])
                        status = 'passed'
                    else:
                        status = 'failed'

                    # Calculate execution time
                    execution_time = int((time.time() - start_time) * 1000)

                    # Take screenshot
                    screenshot_path = f"screenshot_{execution_state['current_step']}.png"
                    page.screenshot(path=screenshot_path)

                    # Update statistics
                    execution_state['stats']['total'] += 1
                    if status == 'passed':
                        execution_state['stats']['passed'] += 1
                    elif status == 'failed':
                        execution_state['stats']['failed'] += 1

                    # Record step result
                    reporter.record_step(step, status, execution_time=execution_time)

                    # Send events
                    execution_state['event_queue'].put({
                        'type': 'step',
                        'data': {
                            'action': step['action'],
                            'selector': step.get('selector', ''),
                            'status': status,
                            'time': execution_time
                        }
                    })

                    execution_state['event_queue'].put({
                        'type': 'screenshot',
                        'data': {
                            'url': screenshot_path
                        }
                    })

                    execution_state['event_queue'].put({
                        'type': 'stats',
                        'data': execution_state['stats']
                    })

                    execution_state['current_step'] += 1

                except Exception as e:
                    # Handle step failure
                    reporter.record_step(step, 'failed', error=str(e))
                    execution_state['stats']['failed'] += 1
                    execution_state['event_queue'].put({
                        'type': 'console',
                        'data': f"Error executing step: {str(e)}"
                    })

            # Test complete
            execution_state['event_queue'].put({
                'type': 'complete',
                'data': None
            })

    except Exception as e:
        execution_state['event_queue'].put({
            'type': 'console',
            'data': f"Test execution error: {str(e)}"
        })
    finally:
        execution_state['running'] = False

@test_runner.route('/get-scheduled-tests')
def get_scheduled_tests():
    return jsonify(scheduled_tests)

@test_runner.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    return send_from_directory(os.path.join('test_runner', 'screenshots'), filename)

@test_runner.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(os.path.join('test_runner', 'uploads'), filename)

@test_runner.route('/reports/<path:filename>')
def serve_report(filename):
    return send_from_directory(os.path.join('test_runner', 'reports'), filename) 

@test_runner.route('/api/record/save', methods=['POST'])
def save_recorded_test_case():
    try:
        data = request.get_json()
        if not data or 'test_suite_id' not in data or 'test_case_name' not in data or 'steps' not in data:
            return jsonify({'error': 'Missing required fields'}), 400

        test_suite_id = str(data['test_suite_id'])
        test_case_name = data['test_case_name']
        steps = data['steps']

        # Save the recorded steps as a JSON file in generated_tests/<suite_id>/recorded/
        save_dir = os.path.join('generated_tests', test_suite_id, 'recorded')
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{test_case_name.replace(' ', '_')}_input.json"
        file_path = os.path.join(save_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'test_suite_id': test_suite_id, 'test_case_name': test_case_name, 'steps': steps}, f, indent=2)

        return jsonify({'success': True, 'message': 'Test case saved successfully', 'file': file_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500