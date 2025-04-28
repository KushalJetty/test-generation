
from flask import Blueprint, render_template, request, jsonify, Response, session, send_from_directory
import os
from playwright.async_api import async_playwright
import asyncio
import threading
import queue
import json
import os
import time
import pandas as pd
import ast
from .test_execution.optimizer import TestOptimizer
from .test_execution.vpn_manager import VPNManager
from .test_execution.reporter import TestReporter, generate_report

bp = Blueprint('routes', __name__)

# Global queues for execution and events
execution_queue = queue.Queue()
event_queue = queue.Queue(maxsize=1000)
scheduled_tests = {}

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

                    start_time = time.time()
                    # Pass the optimizer to _execute_step for dynamic input handling
                    result = await self._execute_step(page, step, config.get('retries', 3), optimizer)
                    execution_time = time.time() - start_time

                    # Record step result
                    reporter.record_step(result, execution_time)

                    # Send step update to client
                    event_queue.put({
                        'type': 'step_update',
                        'data': {
                            'step': i + 1,
                            'total': len(steps),
                            'action': step.get('action'),
                            'selector': step.get('selector', ''),
                            'status': result.get('status', 'unknown'),
                            'time': round(execution_time, 2)
                        }
                    })

                    # Take screenshot if configured or on failure
                    if config.get('screenshots') or result.get('status') == 'failed':
                        screenshot_path = os.path.join('test_runner', 'screenshots', f"step_{i+1}.png")
                        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                        await page.screenshot(path=screenshot_path)
                        event_queue.put({'type': 'screenshot', 'data': screenshot_path})

                    # Stop execution if step failed and stopOnFailure is enabled
                    if result.get('status') == 'failed' and config.get('stopOnFailure', False):
                        event_queue.put({'type': 'error', 'data': f"Test stopped due to failure at step {i+1}"})
                        break

                    # Check again if stop was requested
                    if self.stop_requested:
                        event_queue.put({'type': 'status', 'data': 'Stopping test execution...'})
                        break
        finally:
            # Generate report
            report_path = generate_report(reporter.get_results(), format=config.get('report_format', 'json'), output_dir=os.path.join('test_runner', 'reports'))
            event_queue.put({'type': 'report', 'data': report_path})

            # Disconnect VPN if it was connected
            if vpn_active and config.get('vpn_config'):
                try:
                    with VPNManager(config['vpn_config']) as vpn:
                        await vpn.disconnect()
                        event_queue.put({'type': 'status', 'data': "Disconnected from VPN"})
                except Exception as e:
                    event_queue.put({'type': 'error', 'data': f"VPN disconnection failed: {str(e)}"})

            # Close browser
            await browser.close()

    async def _execute_step(self, page, step, max_retries=3, optimizer=None):
        result = {'step': step, 'status': 'pending', 'retries': 0}

        # Check if this step requires dynamic input
        if step.get('requires_input') and optimizer and optimizer.mode == 'custom-dynamic':
            # Take a screenshot of the element for reference
            selector = step.get('selector')
            if selector:
                try:
                    # Wait for the element to be visible
                    await page.wait_for_selector(selector, state='visible', timeout=10000)

                    # Take a screenshot of the element
                    element = await page.query_selector(selector)
                    if element:
                        screenshot_path = os.path.join('test_runner', 'screenshots', f"element_{selector.replace('#', '').replace('.', '_')}.png")
                        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                        await element.screenshot(path=screenshot_path)

                        # Send the screenshot to the client
                        event_queue.put({
                            'type': 'input_required',
                            'data': {
                                'selector': selector,
                                'screenshot': screenshot_path,
                                'original_value': step.get('value', '')
                            }
                        })

                        # Create a unique ID for this input request
                        input_id = f"input_{int(time.time())}"

                        # Store the input request in a global variable
                        if not hasattr(self, 'pending_inputs'):
                            self.pending_inputs = {}

                        # Create a future to wait for the input
                        input_future = asyncio.Future()
                        self.pending_inputs[input_id] = {
                            'selector': selector,
                            'future': input_future
                        }

                        # Send the input request to the client with the ID
                        event_queue.put({
                            'type': 'input_required',
                            'data': {
                                'input_id': input_id,
                                'selector': selector,
                                'screenshot': screenshot_path,
                                'original_value': step.get('value', '')
                            }
                        })

                        # Wait for the input with a timeout
                        try:
                            # Wait for the future to be resolved
                            value = await asyncio.wait_for(input_future, timeout=60)

                            # Update the step value
                            step['value'] = value

                            # Log the input
                            event_queue.put({
                                'type': 'status',
                                'data': f"Received input for {selector}: {value}"
                            })

                        except asyncio.TimeoutError:
                            # Timeout waiting for input
                            event_queue.put({
                                'type': 'error',
                                'data': f"Timeout waiting for input for {selector}"
                            })

                        except asyncio.TimeoutError:
                            # Timeout waiting for input
                            result['status'] = 'failed'
                            result['message'] = f"Timeout waiting for input for selector: {selector}"
                            return result

                except Exception as e:
                    # Failed to take screenshot or wait for input
                    event_queue.put({
                        'type': 'error',
                        'data': f"Failed to process dynamic input for {selector}: {str(e)}"
                    })

        for attempt in range(max_retries):
            try:
                if step['action'] == 'click':
                    # Wait for the element to be visible and clickable
                    await page.wait_for_selector(step['selector'], state='visible', timeout=10000)
                    await page.click(step['selector'])
                    result['status'] = 'passed'
                    break

                elif step['action'] == 'fill' or step['action'] == 'input':
                    # Wait for the element to be visible
                    await page.wait_for_selector(step['selector'], state='visible', timeout=10000)
                    await page.fill(step['selector'], step.get('value', ''))
                    result['status'] = 'passed'
                    break

                elif step['action'] == 'navigate':
                    await page.goto(step['url'], wait_until='networkidle')
                    result['status'] = 'passed'
                    break

                elif step['action'] == 'wait':
                    if 'selector' in step:
                        await page.wait_for_selector(step['selector'], timeout=step.get('timeout', 30000))
                    elif 'time' in step:
                        await page.wait_for_timeout(step['time'])
                    result['status'] = 'passed'
                    break

                else:
                    result['status'] = 'skipped'
                    result['message'] = f"Unknown action: {step['action']}"
                    break

            except Exception as e:
                result['status'] = 'retry' if attempt < max_retries - 1 else 'failed'
                result['message'] = str(e)
                result['retries'] = attempt + 1

                if attempt < max_retries - 1:
                    # Wait before retry
                    await page.wait_for_timeout(1000)
                else:
                    # Take a screenshot of the failure
                    try:
                        screenshot_path = os.path.join('test_runner', 'screenshots', f"failure_{int(time.time())}.png")
                        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                        await page.screenshot(path=screenshot_path)

                        # Send the failure notification with screenshot
                        event_queue.put({
                            'type': 'step_failure',
                            'data': {
                                'step': step,
                                'message': str(e),
                                'screenshot': screenshot_path
                            }
                        })
                    except:
                        # If screenshot fails, just send the error
                        event_queue.put({
                            'type': 'error',
                            'data': f"Step failed after {max_retries} attempts: {str(e)}"
                        })

        return result

# Initialize the executor thread
executor = AsyncExecutor()
executor.start()

@bp.route('/')
def home():
    return render_template('runner.html')

@bp.route('/upload-test', methods=['POST'])
def upload_test():
    if 'test_file' not in request.files:
        return jsonify({"status": "error", "message": "No test file provided"}), 400

    test_file = request.files['test_file']

    if test_file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400

    # Save the uploaded file
    uploads_dir = os.path.join('test_runner', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, test_file.filename)
    test_file.save(file_path)

    # Parse the test file based on its extension
    try:
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.json':
            # Parse JSON file
            with open(file_path, 'r') as f:
                test_steps = json.load(f)

            # Convert to test configuration
            test_config = {
                "test_steps": test_steps,
                "url": extract_url_from_steps(test_steps)
            }

        elif file_ext == '.py':
            # Parse Python file to extract steps
            test_steps, url = extract_steps_from_python(file_path)

            test_config = {
                "test_steps": test_steps,
                "url": url
            }
        else:
            return jsonify({"status": "error", "message": "Unsupported file format. Please upload a .json or .py file"}), 400

        return jsonify({"status": "success", "test_config": test_config})

    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to parse test file: {str(e)}"}), 400

def extract_url_from_steps(steps):
    """Extract URL from test steps if available"""
    for step in steps:
        if step.get('action') == 'navigate' and 'url' in step:
            return step['url']
    return ""

def extract_steps_from_python(file_path):
    """Extract test steps from a Python test file"""
    import ast
    import re

    with open(file_path, 'r') as f:
        content = f.read()

    # Try to find the URL using regex
    url_match = re.search(r"page\.goto\(['\"]([^'\"]+)['\"]", content)
    url = url_match.group(1) if url_match else ""

    # Parse the Python file
    tree = ast.parse(content)

    steps = []

    # Find all the await expressions
    for node in ast.walk(tree):
        if isinstance(node, ast.Await) and isinstance(node.value, ast.Call):
            call = node.value

            if hasattr(call.func, 'attr'):
                method = call.func.attr

                # Extract click actions
                if method == 'click' and len(call.args) > 0:
                    selector = extract_string_value(call.args[0])
                    if selector:
                        steps.append({
                            "action": "click",
                            "selector": selector
                        })

                # Extract fill/input actions
                elif method == 'fill' and len(call.args) > 1:
                    selector = extract_string_value(call.args[0])
                    value = extract_string_value(call.args[1])
                    if selector and value is not None:
                        steps.append({
                            "action": "fill",
                            "selector": selector,
                            "value": value
                        })

                # Extract navigation actions
                elif method == 'goto' and len(call.args) > 0:
                    url_value = extract_string_value(call.args[0])
                    if url_value:
                        steps.append({
                            "action": "navigate",
                            "url": url_value
                        })
                        # Update URL if not already set
                        if not url:
                            url = url_value

    return steps, url

def extract_string_value(node):
    """Extract string value from an AST node"""
    # For Python 3.8+, use ast.Constant
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    # For backward compatibility with older Python versions
    elif hasattr(ast, 'Str') and isinstance(node, ast.Str):
        return node.s
    return None

@bp.route('/run-test', methods=['POST'])
def run_test():
    config = request.get_json()

    # Validate the test configuration
    if not config:
        return jsonify({"status": "error", "message": "No test configuration provided"}), 400

    # Handle file paths for existing test files
    if config.get('test_file_path'):
        try:
            # Load the test file
            file_path = config['test_file_path']
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == '.json':
                # Load JSON steps
                with open(file_path, 'r') as f:
                    config['test_steps'] = json.load(f)
            elif file_ext == '.py':
                # Extract steps from Python file
                steps, url = extract_steps_from_python(file_path)
                config['test_steps'] = steps
                if not config.get('url') and url:
                    config['url'] = url
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to load test file: {str(e)}"}), 400

    # Add the test to the execution queue
    execution_queue.put(config)

    return jsonify({"status": "queued", "message": "Test has been queued for execution"})

@bp.route('/get-input-fields', methods=['POST'])
def get_input_fields():
    """Get the list of fields that require dynamic input"""
    config = request.get_json()

    if not config or 'test_steps' not in config:
        return jsonify({"status": "error", "message": "Invalid test configuration"}), 400

    # Create an optimizer in dynamic mode
    optimizer = TestOptimizer(mode='custom-dynamic', input_type='dynamic')

    # Process steps to identify input fields
    optimizer.process_steps(config['test_steps'])

    # Get the input fields
    input_fields = optimizer.get_dynamic_input_fields()

    return jsonify({
        "status": "success",
        "input_fields": input_fields
    })

@bp.route('/set-input-value', methods=['POST'])
def set_input_value():
    """Set a dynamic input value for a field"""
    data = request.get_json()

    if not data or 'input_id' not in data or 'value' not in data:
        return jsonify({"status": "error", "message": "Invalid input data"}), 400

    input_id = data['input_id']
    value = data['value']

    # Find the executor thread
    for thread in threading.enumerate():
        if isinstance(thread, AsyncExecutor):
            # Check if the thread has pending inputs
            if hasattr(thread, 'pending_inputs') and input_id in thread.pending_inputs:
                # Get the future
                input_data = thread.pending_inputs[input_id]
                future = input_data['future']

                # Set the result in the future
                asyncio.run_coroutine_threadsafe(
                    _set_future_result(future, value),
                    thread.loop
                )

                # Remove the input from pending inputs
                del thread.pending_inputs[input_id]

                return jsonify({"status": "success"})

    return jsonify({"status": "error", "message": "Input request not found"}), 404

async def _set_future_result(future, result):
    """Set the result of a future"""
    if not future.done():
        future.set_result(result)

@bp.route('/schedule-test', methods=['POST'])
def schedule_test():
    config = request.get_json()

    if not config or 'schedule_time' not in config:
        return jsonify({"status": "error", "message": "Invalid schedule configuration"}), 400

    # Store the scheduled test
    test_id = str(int(time.time()))
    scheduled_tests[test_id] = {
        'config': config,
        'schedule_time': config['schedule_time'],
        'status': 'scheduled'
    }

    return jsonify({"status": "scheduled", "test_id": test_id})

@bp.route('/cancel-test', methods=['POST'])
def cancel_test():
    data = request.get_json()

    if not data or 'test_id' not in data:
        return jsonify({"status": "error", "message": "No test ID provided"}), 400

    test_id = data['test_id']

    if test_id in scheduled_tests:
        scheduled_tests[test_id]['status'] = 'cancelled'
        return jsonify({"status": "success", "message": "Test cancelled successfully"})
    else:
        return jsonify({"status": "error", "message": "Test ID not found"}), 404

@bp.route('/event-stream')
def event_stream():
    def generate():
        while True:
            try:
                event = event_queue.get(timeout=1)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Send a heartbeat to keep the connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                continue
    return Response(generate(), mimetype="text/event-stream")

@bp.route('/get-scheduled-tests')
def get_scheduled_tests():
    return jsonify({"tests": scheduled_tests})

@bp.route('/stop-test', methods=['POST'])
def stop_test():
    """Stop the current test execution"""
    # Find the executor thread
    for thread in threading.enumerate():
        if isinstance(thread, AsyncExecutor):
            # Set a flag to stop execution
            thread.stop_requested = True

            # Log the stop request
            event_queue.put({
                'type': 'status',
                'data': 'Test execution stop requested'
            })

            return jsonify({"status": "success", "message": "Stop request sent"})

    return jsonify({"status": "error", "message": "No active test execution found"})

@bp.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    """Serve screenshot files"""
    return send_from_directory(os.path.join('test_runner', 'screenshots'), filename)

@bp.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    return send_from_directory(os.path.join('test_runner', 'uploads'), filename)

@bp.route('/reports/<path:filename>')
def serve_report(filename):
    """Serve report files"""
    return send_from_directory(os.path.join('test_runner', 'reports'), filename)

