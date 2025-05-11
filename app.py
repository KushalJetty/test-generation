import os
import json
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from playwright.sync_api import sync_playwright
import queue
from validators import url as validate_url
matplotlib.use('Agg')  # Use non-interactive backend for server environment
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, Response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from models import db, Project, TestSuite, TestCase, TestRun, TestResult
from forms import ProjectForm, TestSuiteForm, TestRunForm, FilterForm, ExportForm, TestExecutionForm
import threading
import uuid
import io
import re
import time
from playwright.async_api import async_playwright
import asyncio
from flask_migrate import Migrate
import ast

# Add test runner imports
from test_runner.test_execution.optimizer import TestOptimizer
from test_runner.test_execution.vpn_manager import VPNManager
from test_runner.test_execution.reporter import TestReporter, generate_report

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'streamzai-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///streamzai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SCREENSHOTS_FOLDER'] = 'static/screenshots'
app.config['REPORTS_FOLDER'] = 'reports'

for folder in [app.config['UPLOAD_FOLDER'], app.config['SCREENSHOTS_FOLDER'], app.config['REPORTS_FOLDER']]:
    os.makedirs(folder, exist_ok=True)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Global variables
active_test_runs = {}
execution_state = {
    'running': False,
    'paused': False,
    'current_step': 0,
    'log': [],
    'test_steps': [],
    'target_url': '',
    'headless': True,
    'input_queue': queue.Queue(),
    'awaiting_input': None,
    'reporter': None,
    'event_queue': queue.Queue(),
    'stats': {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'retried': 0
    }
}
recording_actions = []
is_recording = False
driver = None

# Global variables for record test functionality
event_queue = queue.Queue()
browser = None
playwright = None
page = None
tracker = None
recorded_url = None

# Async thread for Playwright operations
class AsyncThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

async_thread = AsyncThread()
async_thread.start()

def run_async(coroutine):
    future = asyncio.run_coroutine_threadsafe(coroutine, async_thread.loop)
    return future.result()

class ActionTracker:
    def __init__(self, page):
        self.page = page
        self.steps = []

    async def start_tracking(self):
        await self.page.expose_function("recordAction", self.record_action)
        await self.page.add_init_script(self.tracking_script())

    async def record_action(self, action):
        self.steps.append(action)
        try:
            event_queue.put_nowait({'type': 'action', 'data': action})
        except queue.Full:
            pass

    def tracking_script(self):
        return """
            (() => {
                function getSelector(el) {
                    if (el.id) return `#${el.id}`;
                    if (el.name) return `[name="${el.name}"]`;
                    if (el.className) return `.${el.className.split(" ").join(".")}`;
                    return el.tagName.toLowerCase();
                }

                document.addEventListener('click', e => {
                    const selector = getSelector(e.target);
                    window.recordAction({
                        action: "click",
                        selector: selector,
                        timestamp: Date.now()
                    });
                }, true);

                document.addEventListener('input', e => {
                    const selector = getSelector(e.target);
                    window.recordAction({
                        action: "input",
                        selector: selector,
                        value: e.target.value,
                        timestamp: Date.now()
                    });
                }, true);
            })();
        """

    def save_steps(self, filename="tests/recorded_steps.json"):
        import os
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            json.dump(self.steps, f, indent=4)

def generate_code(steps):
    global recorded_url
    input_values = {}
    consolidated_steps = []
    
    # Process steps in original sequence but consolidate inputs
    for step in steps:
        if step['action'] == 'click':
            consolidated_steps.append(step)
        elif step['action'] == 'input':
            # Track input values but maintain sequence
            input_values[step['selector']] = step['value']
            
    # Save input values to JSON
    import os
    # Generate unique filename
    from urllib.parse import urlparse
    import datetime
    domain = urlparse(recorded_url).netloc.replace('.', '_')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"{domain}_{timestamp}_input.json"
    json_path = os.path.join('tests', json_filename)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w') as f:
        json.dump(input_values, f, indent=4)
    
    # Generate code
    code = [
        "from playwright.async_api import async_playwright\n",
        "import asyncio\n\n",
        "async def test_recorded_actions():\n",
        "    async with async_playwright() as p:\n",
        "        browser = await p.chromium.launch(headless=False)\n",
        "        page = await browser.new_page()\n",
        f"        await page.goto('{recorded_url}')\n"
    ]
    
    # Add steps in original sequence
    for step in steps:
        if step['action'] == 'click':
            code.append(f"        await page.click('{step['selector']}')\n")
        elif step['action'] == 'input':
            # Only add input if it's the final value for this selector
            if input_values.get(step['selector']) == step['value']:
                code.append(f"        await page.fill('{step['selector']}', '{step['value']}')\n")
    
    code.append("        await browser.close()\n")
    code.append("asyncio.run(test_recorded_actions())")
    return ''.join(code)

@app.route('/test-case/upload', methods=['GET', 'POST'])
def upload_test_case():
    """Handle test case file upload."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if file and file.filename.endswith('.json'):
            filename = secure_filename(file.filename)
            filepath = os.path.join('uploads', filename)
            
            # Ensure upload directory exists
            os.makedirs('uploads', exist_ok=True)
            
            try:
                file.save(filepath)
                with open(filepath) as f:
                    test_steps = json.load(f)
                    execution_state['test_steps'] = test_steps
                    return jsonify({'message': 'Test case uploaded successfully'})
            except json.JSONDecodeError:
                os.remove(filepath)
                return jsonify({'error': 'Invalid JSON file'}), 400
            except Exception as e:
                return jsonify({'error': f'Error processing file: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Invalid file type. Please upload a JSON file'}), 400
    
    return render_template('test_run_form.html')

@app.route('/test-case/execute', methods=['POST'])
def execute_test():
    """Execute a test case using Playwright."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        target_url = data.get('target_url', '').strip()
        if not target_url:
            return jsonify({'error': 'Target URL is required'}), 400

        if not validate_url(target_url):
            return jsonify({'error': 'Invalid URL format'}), 400

        # Check if test steps are loaded
        if not execution_state['test_steps']:
            return jsonify({'error': 'No test steps loaded. Please upload a test case file first.'}), 400

        execution_state['target_url'] = target_url
        execution_state['headless'] = data.get('headless', True)
        execution_state['running'] = True
        execution_state['paused'] = False
        execution_state['log'] = []

        thread = threading.Thread(target=execute_test_case)
        thread.daemon = True
        thread.start()

        return jsonify({'message': 'Test execution started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-case/pause', methods=['POST'])
def pause_test():
    """Pause or resume test execution."""
    execution_state['paused'] = not execution_state['paused']
    status = 'paused' if execution_state['paused'] else 'resumed'
    return jsonify({'status': f'Test execution {status}'})

@app.route('/test-case/stop', methods=['POST'])
def stop_test():
    """Stop test execution."""
    execution_state['running'] = False
    execution_state['paused'] = False
    return jsonify({'status': 'Test execution stopped'})

@app.route('/test-case/status')
def get_test_status():
    """Get current test execution status."""
    return jsonify({
        'running': execution_state['running'],
        'paused': execution_state['paused'],
        'current_step': execution_state['current_step'],
        'log': execution_state['log']
    })

@app.route('/test-case/awaiting_input')
def check_awaiting_input():
    """Check if test execution is waiting for input."""
    var_name = execution_state['awaiting_input']
    if var_name:
        return jsonify({
            'awaiting': True,
            'var_name': var_name,
            'timestamp': time.time()  # Add timestamp to prevent caching
        })
    return jsonify({'awaiting': False})

@app.route('/test-case/submit_input', methods=['POST'])
def submit_input():
    """Submit input for test execution."""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({'error': 'No data provided'}), 400
            
        value = data.get('value')
        # Put the value in the queue
        execution_state['input_queue'].put(value)
        log_message(f"Received input value from user")
        return jsonify({'success': True})
    except Exception as e:
        log_message(f"Error processing input: {str(e)}")
        return jsonify({'error': str(e)}), 500

def log_message(msg):
    execution_state['log'].append(msg)

def execute_test_case():
    """Execute test case using Playwright."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=execution_state['headless'])
        context = browser.new_context()
        page = context.new_page()
        reporter = TestReporter()
        
        try:
            # Navigate to target URL
            page.goto(execution_state['target_url'])
            page.wait_for_load_state('networkidle')
            
            # Execute test steps
            for idx, step in enumerate(execution_state['test_steps']):
                if not execution_state['running']:
                    break
                    
                while execution_state['paused']:
                    time.sleep(0.5)
                    continue
                    
                execution_state['current_step'] = idx
                action = step.get('action', '')
                selector = step.get('selector', '')
                value = step.get('value', '')
                
                try:
                    if selector:
                        element = page.wait_for_selector(selector, state='visible', timeout=10000)
                        if not element:
                            reporter.record_step(step, 'error', f"Element not found: {selector}")
                            continue
                    
                    if action == 'click':
                        page.click(selector)
                        reporter.record_step(step, 'success')
                    elif action in ['fill', 'type', 'input']:
                        page.fill(selector, value)
                        reporter.record_step(step, 'success')
                    elif action == 'wait':
                        wait_time = int(value) if value else 1000
                        page.wait_for_timeout(wait_time)
                        reporter.record_step(step, 'success')
                    elif action == 'navigate':
                        page.goto(value)
                        page.wait_for_load_state('networkidle')
                        reporter.record_step(step, 'success')
                    
                except Exception as e:
                    reporter.record_step(step, 'error', str(e))
            
            # Generate report
            report_path = generate_report(reporter, 'html')
            execution_state['log'].append(f"Test execution completed. Report saved to: {report_path}")
            
        except Exception as e:
            execution_state['log'].append(f"Error during test execution: {str(e)}")
        finally:
            browser.close()
            execution_state['running'] = False

def generate_chart(data, chart_type='pie', filename=None):
    """Generate a chart based on test results data.
    
    Args:
        data: Dictionary with test result counts
        chart_type: Type of chart to generate ('pie', 'bar', etc.)
        filename: Optional filename to save the chart
        
    Returns:
        Path to the saved chart image
    """
    plt.figure(figsize=(8, 6))
    
    if chart_type == 'pie':
        # Create a pie chart
        labels = list(data.keys())
        sizes = list(data.values())
        colors = ['#28a745', '#dc3545', '#ffc107', '#6c757d']
        explode = (0.1, 0, 0, 0)  # explode the 1st slice (passed)
        
        plt.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=140)
        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        plt.title('Test Results Distribution')
        
    elif chart_type == 'bar':
        # Create a bar chart
        categories = list(data.keys())
        values = list(data.values())
        colors = ['#28a745', '#dc3545', '#ffc107', '#6c757d']
        
        plt.bar(categories, values, color=colors)
        plt.xlabel('Status')
        plt.ylabel('Count')
        plt.title('Test Results by Status')
    
    # Save the chart
    if not filename:
        filename = f"chart_{uuid.uuid4().hex[:8]}.png"
    
    chart_dir = os.path.join(app.static_folder, 'charts')
    os.makedirs(chart_dir, exist_ok=True)
    chart_path = os.path.join(chart_dir, filename)
    
    plt.savefig(chart_path)
    plt.close()
    
    return os.path.join('static', 'charts', filename)

def run_tests_async(test_run_id):
    """Run tests asynchronously for a test run.
    
    Args:
        test_run_id: ID of the test run to execute
    """
    with app.app_context():
        test_run = TestRun.query.get(test_run_id)
        if not test_run:
            logger.error(f"Test run {test_run_id} not found")
            return
        
        # Update test run status
        test_run.status = 'running'
        test_run.start_time = datetime.datetime.utcnow()
        db.session.commit()
        
        try:
            # Get test suite and test cases
            test_suite = test_run.test_suite
            test_cases = test_suite.test_cases
            
            # Import the test runner
            from folder_analyser.test_runner import StreamzAITestRunner
            
            # Collect test files to run
            test_files = []
            for test_case in test_cases:
                if os.path.exists(test_case.test_file_path):
                    test_files.append(test_case.test_file_path)
                else:
                    # Create a test result for missing test file
                    test_result = TestResult(
                        test_case_id=test_case.id,
                        test_run_id=test_run.id,
                        status='error',
                        error_message=f"Test file not found: {test_case.test_file_path}"
                    )
                    db.session.add(test_result)
                    db.session.commit()
            
            # Initialize the test runner
            runner = StreamzAITestRunner()
            
            # Run tests for each test case
            for test_case in test_cases:
                # Create test result
                test_result = TestResult(
                    test_case_id=test_case.id,
                    test_run_id=test_run.id,
                    status='running'
                )
                db.session.add(test_result)
                db.session.commit()
                
                try:
                    # Execute the test using the test runner
                    if os.path.exists(test_case.test_file_path):
                        # Run the test file
                        result = runner.run_test_file(test_case.test_file_path)
                        
                        # Update test result based on the runner output
                        status = result['status']
                        execution_time = result['execution_time']
                        
                        # Get error message if any
                        error_message = None
                        if status in ['failed', 'error']:
                            # Find the first error or failure message
                            for test_info in result['tests']:
                                if test_info['status'] in ['failed', 'error']:
                                    error_message = test_info['error_message']
                                    break
                        
                        # Update test result
                        test_result.status = status
                        test_result.execution_time = execution_time
                        test_result.error_message = error_message
                        db.session.commit()
                    else:
                        # Test file doesn't exist
                        test_result.status = 'error'
                        test_result.error_message = f"Test file not found: {test_case.test_file_path}"
                        db.session.commit()
                    
                except Exception as e:
                    # Handle test execution error
                    logger.error(f"Error executing test case {test_case.id}: {str(e)}")
                    test_result.status = 'error'
                    test_result.error_message = str(e)
                    db.session.commit()
            
            # Update test run status
            test_run.status = 'completed'
            test_run.end_time = datetime.datetime.utcnow()
            db.session.commit()
            
            # Remove from active test runs
            if test_run_id in active_test_runs:
                del active_test_runs[test_run_id]
                
        except Exception as e:
            # Handle overall test run error
            logger.error(f"Error in test run {test_run_id}: {str(e)}")
            test_run.status = 'failed'
            test_run.end_time = datetime.datetime.utcnow()
            db.session.commit()
            
            # Remove from active test runs
            if test_run_id in active_test_runs:
                del active_test_runs[test_run_id]

# Routes
@app.route('/')
def index():
    """Dashboard home page."""
    # Get counts for dashboard
    projects_count = Project.query.count()
    test_suites_count = TestSuite.query.count()
    test_runs_count = TestRun.query.count()
    
    # Calculate success rate
    passed_results = TestResult.query.filter_by(status='passed').count()
    total_results = TestResult.query.count()
    success_rate = round((passed_results / total_results) * 100) if total_results > 0 else 0
    
    # Get recent test runs
    recent_test_runs = TestRun.query.order_by(TestRun.created_at.desc()).limit(5).all()
    
    # Get recent projects
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
    
    # Generate chart for test results
    test_results = {
        'Passed': TestResult.query.filter_by(status='passed').count(),
        'Failed': TestResult.query.filter_by(status='failed').count(),
        'Skipped': TestResult.query.filter_by(status='skipped').count(),
        'Error': TestResult.query.filter_by(status='error').count()
    }
    
    chart_path = None
    if sum(test_results.values()) > 0:
        chart_path = generate_chart(test_results)
    
    return render_template('index.html',
                           projects_count=projects_count,
                           test_suites_count=test_suites_count,
                           test_runs_count=test_runs_count,
                           success_rate=success_rate,
                           recent_test_runs=recent_test_runs,
                           recent_projects=recent_projects,
                           chart_path=chart_path)

@app.route('/projects')
def projects():
    """List all projects."""
    projects = Project.query.filter_by(active=True).order_by(Project.name).all()
    return render_template('projects.html', projects=projects)

@app.route('/project/create', methods=['GET', 'POST'])
def create_project():
    """Create a new project."""
    form = ProjectForm()
    
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            path=form.path.data,
            description=form.description.data
        )
        db.session.add(project)
        db.session.commit()
        
        flash('Project created successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))
    
    return render_template('project_form.html', form=form, title='Create Project')

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """Show project details."""
    project = Project.query.get_or_404(project_id)
    test_suites = TestSuite.query.filter_by(project_id=project_id, active=True).all()
    
    # Get test statistics for this project
    test_stats = {}
    for test_suite in test_suites:
        for test_run in TestRun.query.filter_by(test_suite_id=test_suite.id, active=True).all():
            passed = TestResult.query.filter_by(test_run_id=test_run.id, status='passed', active=True).count()
            failed = TestResult.query.filter_by(test_run_id=test_run.id, status='failed', active=True).count()
            skipped = TestResult.query.filter_by(test_run_id=test_run.id, status='skipped', active=True).count()
            error = TestResult.query.filter_by(test_run_id=test_run.id, status='error', active=True).count()
            
            test_stats[test_run.id] = {
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'error': error,
                'total': passed + failed + skipped + error
            }
    
    return render_template('project_detail.html', project=project, test_suites=test_suites, test_stats=test_stats)

@app.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
def edit_project(project_id):
    """Edit an existing project."""
    project = Project.query.get_or_404(project_id)
    form = ProjectForm(obj=project)
    
    if form.validate_on_submit():
        project.name = form.name.data
        project.path = form.path.data
        project.description = form.description.data
        db.session.commit()
        
        flash('Project updated successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))
    
    return render_template('project_form.html', form=form, title='Edit Project')

@app.route('/project/<int:project_id>/delete', methods=['POST'])
def delete_project(project_id):
    """Delete a project."""
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    
    flash('Project deleted successfully!', 'success')
    return redirect(url_for('projects'))

@app.route('/test-suites')
def test_suites():
    """List all test suites."""
    test_suites = TestSuite.query.filter_by(active=True).order_by(TestSuite.name).all()
    return render_template('test_suites.html', test_suites=test_suites)

@app.route('/test-suite/create', methods=['GET', 'POST'])
@app.route('/project/<int:project_id>/test-suite/create', methods=['GET', 'POST'])
def create_test_suite(project_id=None):
    """Create a new test suite."""
    form = TestSuiteForm()
    
    # Populate project choices
    form.project_id.choices = [(p.id, p.name) for p in Project.query.order_by(Project.name).all()]
    
    # If project_id is provided, preselect it
    if project_id:
        form.project_id.data = project_id
    
    if form.validate_on_submit():
        try:
            # Get the project
            project = Project.query.get(form.project_id.data)
            if not project:
                flash('Project not found.', 'error')
                return redirect(url_for('test_suites'))

            # Create test suite
            test_suite = TestSuite(
                name=form.name.data,
                description=form.description.data,
                project_id=form.project_id.data
            )
            db.session.add(test_suite)
            db.session.commit()

            # Initialize test generator
            generator = StreamzAITestGenerator()
            
            # Generate test cases
            results = generator.generate_tests(project.path, os.path.join('generated_tests', str(test_suite.id)))
            
            # Create test cases in database
            for test_file in results.get('test_files', []):
                if test_file['status'] == 'success':
                    test_case = TestCase(
                        name=os.path.basename(test_file['test_file']),
                        description=f"Generated from {test_file['original_file']}",
                        test_file_path=test_file['test_file'],
                        test_suite_id=test_suite.id
                    )
                    db.session.add(test_case)
            
            db.session.commit()
            flash('Test suite created successfully!', 'success')
            return redirect(url_for('test_suites'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating test suite: {str(e)}', 'error')
            return redirect(url_for('test_suites'))

    return render_template('test_suite_form.html', form=form, title='Create Test Suite')

@app.route('/test-suite/<int:suite_id>')
def test_suite_detail(suite_id):
    """Show test suite details."""
    test_suite = TestSuite.query.get_or_404(suite_id)
    test_cases = TestCase.query.filter_by(test_suite_id=suite_id, active=True).all()
    test_runs = TestRun.query.filter_by(test_suite_id=suite_id, active=True).all()
    
    return render_template('test_suite_detail.html', test_suite=test_suite, test_cases=test_cases, test_runs=test_runs)

@app.route('/test-suite/<int:suite_id>/edit', methods=['GET', 'POST'])
def edit_test_suite(suite_id):
    """Edit an existing test suite."""
    test_suite = TestSuite.query.get_or_404(suite_id)
    form = TestSuiteForm(obj=test_suite)
    
    # Populate project choices
    form.project_id.choices = [(p.id, p.name) for p in Project.query.order_by(Project.name).all()]
    
    if form.validate_on_submit():
        test_suite.name = form.name.data
        test_suite.description = form.description.data
        test_suite.project_id = form.project_id.data
        db.session.commit()
        
        flash('Test suite updated successfully!', 'success')
        return redirect(url_for('test_suite_detail', suite_id=test_suite.id))
    
    return render_template('test_suite_form.html', form=form, title='Edit Test Suite')

@app.route('/test-suite/<int:suite_id>/delete', methods=['POST'])
def delete_test_suite(suite_id):
    """Delete a test suite."""
    test_suite = TestSuite.query.get_or_404(suite_id)
    db.session.delete(test_suite)
    db.session.commit()
    
    flash('Test suite deleted successfully!', 'success')
    return redirect(url_for('test_suites'))

@app.route('/test-runs')
def test_runs():
    """List all test runs."""
    test_runs = TestRun.query.filter_by(active=True).order_by(TestRun.created_at.desc()).all()
    return render_template('test_runs.html', test_runs=test_runs)

@app.route('/test-run/create', methods=['GET', 'POST'])
@app.route('/test-suite/<int:suite_id>/test-run/create', methods=['GET', 'POST'])
def create_test_run(suite_id=None):
    """Create a new test run."""
    form = TestRunForm()
    
    # Populate test suite choices
    form.test_suite_id.choices = [(ts.id, f"{ts.name} ({ts.project.name})") for ts in TestSuite.query.join(Project).order_by(TestSuite.name).all()]
    
    # If suite_id is provided, preselect it
    if suite_id:
        form.test_suite_id.data = suite_id
    
    if form.validate_on_submit():
        test_run = TestRun(
            name=form.name.data,
            test_suite_id=form.test_suite_id.data,
            status='pending'
        )
        db.session.add(test_run)
        db.session.commit()
        
        # Start test run asynchronously
        thread = threading.Thread(target=run_tests_async, args=(test_run.id,))
        thread.daemon = True
        thread.start()
        
        # Store thread in active test runs
        active_test_runs[test_run.id] = thread
        
        flash('Test run started!', 'success')
        return redirect(url_for('test_run_detail', run_id=test_run.id))
    
    return render_template('test_run_form.html', form=form, title='Create Test Run')

@app.route('/test-run/<int:run_id>')
def test_run_detail(run_id):
    """Show test run details."""
    test_run = TestRun.query.get_or_404(run_id)
    test_results = TestResult.query.filter_by(test_run_id=test_run.id, active=True).all()
    
    # Calculate summary
    summary = {
        'passed': TestResult.query.filter_by(test_run_id=test_run.id, status='passed', active=True).count(),
        'failed': TestResult.query.filter_by(test_run_id=test_run.id, status='failed', active=True).count(),
        'skipped': TestResult.query.filter_by(test_run_id=test_run.id, status='skipped', active=True).count(),
        'error': TestResult.query.filter_by(test_run_id=test_run.id, status='error', active=True).count()
    }
    summary['total'] = sum(summary.values())
    
    # Generate chart
    chart_data = {
        'Passed': summary['passed'],
        'Failed': summary['failed'],
        'Skipped': summary['skipped'],
        'Error': summary['error']
    }
    
    chart_path = None
    if summary['total'] > 0:
        chart_path = generate_chart(chart_data, filename=f"run_{run_id}_results.png")
    
    return render_template('test_run_detail.html', test_run=test_run, test_results=test_results, summary=summary, chart_path=chart_path)

@app.route('/reports')
def reports():
    """Show test reports."""
    filter_form = FilterForm()
    export_form = ExportForm()
    
    # Populate filter form choices
    filter_form.project.choices = [(0, 'All')] + [(p.id, p.name) for p in Project.query.order_by(Project.name).all()]
    filter_form.test_suite_id.choices = [(0, 'All')] + [(ts.id, ts.name) for ts in TestSuite.query.order_by(TestSuite.name).all()]
    
    # Apply filters
    query = TestResult.query.join(TestRun).join(TestCase).join(TestSuite).join(Project)
    
    if request.args.get('project') and request.args.get('project') != '0':
        query = query.filter(Project.id == request.args.get('project'))
        filter_form.project.data = int(request.args.get('project'))
    
    if request.args.get('test_suite') and request.args.get('test_suite') != '0':
        query = query.filter(TestSuite.id == request.args.get('test_suite'))
        filter_form.test_suite_id.data = int(request.args.get('test_suite'))
    
    if request.args.get('status') and request.args.get('status') != '':
        query = query.filter(TestResult.status == request.args.get('status'))
        filter_form.status.data = request.args.get('status')
    
    if request.args.get('date_from'):
        date_from = datetime.datetime.strptime(request.args.get('date_from'), '%Y-%m-%d')
        query = query.filter(TestResult.created_at >= date_from)
        filter_form.date_from.data = date_from
    
    if request.args.get('date_to'):
        date_to = datetime.datetime.strptime(request.args.get('date_to'), '%Y-%m-%d')
        date_to = date_to.replace(hour=23, minute=59, second=59)
        query = query.filter(TestResult.created_at <= date_to)
        filter_form.date_to.data = date_to
    
    # Get results
    results = query.order_by(TestResult.created_at.desc()).all()
    
    # Calculate summary
    summary = {
        'passed': sum(1 for r in results if r.status == 'passed'),
        'failed': sum(1 for r in results if r.status == 'failed'),
        'skipped': sum(1 for r in results if r.status == 'skipped'),
        'error': sum(1 for r in results if r.status == 'error')
    }
    summary['total'] = len(results)
    
    # Generate chart
    chart_data = {
        'Passed': summary['passed'],
        'Failed': summary['failed'],
        'Skipped': summary['skipped'],
        'Error': summary['error']
    }
    
    chart_path = None
    if summary['total'] > 0:
        chart_path = generate_chart(chart_data, chart_type='bar', filename="report_results.png")
    
    return render_template('reports.html', results=results, summary=summary, chart_path=chart_path, filter_form=filter_form, export_form=export_form)

@app.route('/export', methods=['POST'])
def export_results():
    """Export test results."""
    form = ExportForm()
    
    if form.validate_on_submit():
        # Apply filters (same as in reports view)
        query = TestResult.query.join(TestRun).join(TestCase).join(TestSuite).join(Project)
        
        if request.args.get('project') and request.args.get('project') != '0':
            query = query.filter(Project.id == request.args.get('project'))
        
        if request.args.get('test_suite') and request.args.get('test_suite') != '0':
            query = query.filter(TestSuite.id == request.args.get('test_suite'))
        
        if request.args.get('status') and request.args.get('status') != '':
            query = query.filter(TestResult.status == request.args.get('status'))
        
        if request.args.get('date_from'):
            date_from = datetime.datetime.strptime(request.args.get('date_from'), '%Y-%m-%d')
            query = query.filter(TestResult.created_at >= date_from)
        
        if request.args.get('date_to'):
            date_to = datetime.datetime.strptime(request.args.get('date_to'), '%Y-%m-%d')
            date_to = date_to.replace(hour=23, minute=59, second=59)
            query = query.filter(TestResult.created_at <= date_to)
        
        # Get results
        results = query.order_by(TestResult.created_at.desc()).all()
        
        # Prepare data for export
        data = []
        for result in results:
            row = {
                'Test Case': result.test_case.test_file_path,
                'Original File': result.test_case.original_file_path,
                'Language': result.test_case.language,
                'Status': result.status,
                'Execution Time (s)': result.execution_time,
                'Test Run': result.test_run.name,
                'Test Suite': result.test_run.test_suite.name,
                'Project': result.test_run.test_suite.project.name,
                'Date': result.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if form.include_details.data and result.error_message:
                row['Error Message'] = result.error_message
            
            data.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Export based on selected format
        if form.format.data == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name='test_results.csv'
            )
            
        elif form.format.data == 'excel':
            output = io.BytesIO()
            df.to_excel(output, index=False)
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='test_results.xlsx'
            )
            
        elif form.format.data == 'json':
            output = df.to_json(orient='records')
            
            return send_file(
                io.BytesIO(output.encode('utf-8')),
                mimetype='application/json',
                as_attachment=True,
                download_name='test_results.json'
            )
    
    flash('Invalid export parameters', 'error')
    return redirect(url_for('reports'))

# API Routes
@app.route('/api/test-run/<int:run_id>/status')
def api_test_run_status(run_id):
    """Get test run status."""
    test_run = TestRun.query.get_or_404(run_id)
    return jsonify({
        'id': test_run.id,
        'name': test_run.name,
        'status': test_run.status,
        'start_time': test_run.start_time.isoformat() if test_run.start_time else None,
        'end_time': test_run.end_time.isoformat() if test_run.end_time else None
    })

@app.route('/api/test-run/<int:run_id>/results')
def api_test_run_results(run_id):
    """Get test run results."""
    test_run = TestRun.query.get_or_404(run_id)
    test_results = TestResult.query.filter_by(test_run_id=test_run.id).all()
    
    # Calculate summary
    summary = {
        'passed': TestResult.query.filter_by(test_run_id=test_run.id, status='passed').count(),
        'failed': TestResult.query.filter_by(test_run_id=test_run.id, status='failed').count(),
        'skipped': TestResult.query.filter_by(test_run_id=test_run.id, status='skipped').count(),
        'error': TestResult.query.filter_by(test_run_id=test_run.id, status='error').count(),
        'total': TestResult.query.filter_by(test_run_id=test_run.id).count()
    }
    
    # Format results
    results = []
    for result in test_results:
        results.append({
            'id': result.id,
            'status': result.status,
            'execution_time': result.execution_time,
            'error_message': result.error_message,
            'created_at': result.created_at.isoformat(),
            'test_case': {
                'id': result.test_case.id,
                'original_file_path': result.test_case.original_file_path,
                'test_file_path': result.test_case.test_file_path,
                'language': result.test_case.language
            }
        })
    
    return jsonify({
        'summary': summary,
        'results': results
    })

@app.route('/test-suite/<int:suite_id>/run', methods=['GET'])
def run_test_suite(suite_id):
    """Run a test suite by redirecting to create_test_run."""
    return redirect(url_for('create_test_run', suite_id=suite_id))

@app.route('/api/record/start', methods=['POST'])
def handle_start():
    global recorded_url
    data = request.get_json()
    recorded_url = data.get('url', 'https://test.teamstreamz.com/')
    run_async(start_recording())
    return jsonify({'status': 'success', 'message': 'Recording started'})

@app.route('/api/record/clear', methods=['POST'])
def handle_clear():
    run_async(clear_recording())
    return jsonify({'status': 'success', 'message': 'Recording cleared'})

@app.route('/api/record/stream')
def stream():
    def event_stream():
        while True:
            try:
                event = event_queue.get(timeout=1)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                continue
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/api/record/stop', methods=['POST'])
def handle_stop():
    result = run_async(stop_recording())
    return jsonify(result)

@app.route('/api/record/save', methods=['POST'])
def save_recorded_test():
    """Save a recorded test as a test case in the database."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        suite_id = data.get('suite_id')
        code = data.get('code')
        test_name = data.get('name', f"Recorded Test {datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
        
        if not suite_id or not code:
            return jsonify({'error': 'Missing required fields (suite_id, code)'}), 400
            
        # Get the test suite
        test_suite = TestSuite.query.get_or_404(suite_id)
        
        # Create test file directory if it doesn't exist
        test_dir = os.path.join('generated_tests', str(suite_id), 'recorded')
        os.makedirs(test_dir, exist_ok=True)
        
        # Generate a unique filename
        filename = f"{test_name.replace(' ', '_').lower()}.py"
        filepath = os.path.join(test_dir, filename)
        
        # Write the code to the file
        with open(filepath, 'w') as f:
            f.write(code)
        
        # Create a new test case in the database
        test_case = TestCase(
            name=test_name,
            description=f"Recorded test for {test_suite.name}",
            original_file_path="recorded",
            test_file_path=filepath,
            language="python",
            status="generated",
            test_suite_id=suite_id
        )
        
        db.session.add(test_case)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Test case saved successfully',
            'test_case_id': test_case.id,
            'test_file': filepath
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

async def clear_recording():
    global tracker
    if tracker:
        tracker.steps = []
    while not event_queue.empty():
        try:
            event_queue.get_nowait()
        except queue.Empty:
            break
    event_queue.put({'type': 'clear', 'data': None})

async def start_recording():
    global browser, playwright, page, tracker
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()
    tracker = ActionTracker(page)
    await tracker.start_tracking()
    await page.goto(recorded_url)

async def stop_recording():
    global browser, playwright, tracker
    tracker.save_steps()
    code = generate_code(tracker.steps)
    event_queue.put({'type': 'code', 'data': code})
    await browser.close()
    await playwright.stop()
    return {'steps': tracker.steps, 'code': code}


@app.route('/test-runner')
def test_runner():
    """Main test runner page."""
    return render_template('test_run_form.html')

@app.route('/test-runner/upload', methods=['POST'])
def upload_test_file():
    """Handle test case file upload."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and (file.filename.endswith('.json') or file.filename.endswith('.py')):
        # Save the uploaded file
        upload_dir = app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_dir, secure_filename(file.filename))
        file.save(file_path)
        
        try:
            if file.filename.endswith('.json'):
                with open(file_path, 'r') as f:
                    test_config = json.load(f)
                return jsonify({'success': True, 'config': test_config})
            else:
                steps = extract_steps_from_python(file_path)
                return jsonify({'success': True, 'config': {'test_steps': steps}})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Unsupported file type'}), 400

@app.route('/test-runner/execute', methods=['POST'])
def execute_test_runner():
    """Start test execution."""
    if execution_state['running']:
        return jsonify({'error': 'Test already running'}), 400

    test_config = request.get_json()
    if not test_config:
        return jsonify({'error': 'No test configuration provided'}), 400

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
    thread = threading.Thread(target=run_test_case, args=(test_config,))
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Test execution started'})

@app.route('/test-runner/stop', methods=['POST'])
def stop_test_runner():
    """Stop test execution."""
    execution_state['running'] = False
    return jsonify({'message': 'Test execution stopped'})

@app.route('/test-runner/events')
def test_runner_events():
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

def run_test_case(config):
    """Execute the test case."""
    try:
        with sync_playwright() as p:
            # Launch browser based on configuration
            browser_type = getattr(p, config.get('browser', 'chromium'))
            browser = browser_type.launch(headless=config.get('headless', False))
            context = browser.new_context()
            page = context.new_page()
            
            # Initialize components
            reporter = execution_state['reporter']
            optimizer = TestOptimizer(config.get('mode', 'default'), config.get('inputs'))

            # Setup event handlers
            page.on("console", lambda msg: execution_state['event_queue'].put({
                'type': 'console',
                'data': f"{msg.type}: {msg.text}"
            }))

            try:
                # Navigate to initial URL if provided
                if config.get('url'):
                    page.goto(config['url'])
                    reporter.record_step({'action': 'navigate', 'value': config['url']}, 'passed')

                # Process and execute test steps
                if config.get('test_steps'):
                    steps = optimizer.process_steps(config['test_steps'])
                    
                    for step in steps:
                        if not execution_state['running']:
                            break
                        
                        try:
                            start_time = time.time()
                            
                            # Execute step based on action type
                            if step['action'] == 'click':
                                page.click(step['selector'])
                            elif step['action'] in ['fill', 'type']:
                                page.fill(step['selector'], step['value'])
                            elif step['action'] == 'select':
                                page.select_option(step['selector'], step['value'])
                            elif step['action'] == 'check':
                                page.check(step['selector'])
                            elif step['action'] == 'uncheck':
                                page.uncheck(step['selector'])
                            
                            execution_time = int((time.time() - start_time) * 1000)
                            status = 'passed'
                            
                            # Take screenshot
                            screenshot_path = f"screenshot_{execution_state['current_step']}.png"
                            page.screenshot(path=os.path.join(app.config['SCREENSHOTS_FOLDER'], screenshot_path))
                            
                            # Update statistics
                            execution_state['stats']['total'] += 1
                            execution_state['stats']['passed'] += 1
                            
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
                                    'url': f"/static/screenshots/{screenshot_path}"
                                }
                            })
                            
                            execution_state['event_queue'].put({
                                'type': 'stats',
                                'data': execution_state['stats']
                            })
                            
                            execution_state['current_step'] += 1
                            
                        except Exception as e:
                            # Handle step failure
                            execution_state['stats']['failed'] += 1
                            reporter.record_step(step, 'failed', error=str(e))
                            execution_state['event_queue'].put({
                                'type': 'console',
                                'data': f"Error executing step: {str(e)}"
                            })
                            
                            if config.get('stopOnFailure'):
                                break
                
                # Generate report
                if config.get('reportFormat'):
                    report_path = generate_report(reporter, config['reportFormat'])
                    execution_state['event_queue'].put({
                        'type': 'report',
                        'data': {'url': f"/reports/{os.path.basename(report_path)}"}
                    })
            
            finally:
                browser.close()
                
    except Exception as e:
        execution_state['event_queue'].put({
            'type': 'error',
            'data': f"Test execution error: {str(e)}"
        })
    finally:
        execution_state['running'] = False
        execution_state['event_queue'].put({
            'type': 'complete',
            'data': None
        })

def extract_steps_from_python(file_path):
    """Extract test steps from Python file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    steps = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and hasattr(node.func.value, 'id') and node.func.value.id == 'page':
                action = node.func.attr
                if action in ['goto', 'click', 'fill', 'type', 'select_option', 'check', 'uncheck']:
                    step = {'action': action}
                    
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
    """Extract string value from AST node."""
    if isinstance(node, ast.Str):
        return node.s
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None

@app.route('/static/screenshots/<path:filename>')
def serve_screenshot(filename):
    """Serve screenshot files."""
    return send_from_directory(app.config['SCREENSHOTS_FOLDER'], filename)

@app.route('/reports/<path:filename>')
def serve_report(filename):
    """Serve report files."""
    return send_from_directory(app.config['REPORTS_FOLDER'], filename)

@app.route('/test-case/<int:case_id>/download')
def download_test_case(case_id):
    """Download a test case file."""
    test_case = TestCase.query.get_or_404(case_id)
    
    if not os.path.exists(test_case.test_file_path):
        flash('Test file not found.', 'error')
        return redirect(url_for('test_suite_detail', suite_id=test_case.test_suite_id))
    
    return send_file(test_case.test_file_path, 
                    as_attachment=True, 
                    download_name=f"{test_case.name.replace(' ', '_')}.py")

@app.route('/test-case/<int:case_id>')
def test_case_detail(case_id):
    """Show test case details."""
    test_case = TestCase.query.get_or_404(case_id)
    
    # Get file content if it exists
    file_content = None
    if os.path.exists(test_case.test_file_path):
        try:
            with open(test_case.test_file_path, 'r') as f:
                file_content = f.read()
        except Exception as e:
            file_content = f"Error reading file: {str(e)}"
    
    # Get test results for this test case
    test_results = TestResult.query.filter_by(test_case_id=case_id, active=True).all()
    
    return render_template('test_case_detail.html', 
                           test_case=test_case, 
                           test_results=test_results, 
                           file_content=file_content)

# Test Runner API routes
@app.route('/api/test-runner/upload', methods=['POST'])
def api_upload_test_file():
    """Handle test file upload for the test runner API."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    suite_id = request.form.get('suite_id')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.py'):
        filename = secure_filename(file.filename)
        # Create uploads/test_runner directory if it doesn't exist
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'test_runner')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        return jsonify({
            'success': True,
            'filename': filename,
            'path': file_path
        })

    return jsonify({'error': 'File type not allowed. Only Python files are accepted.'}), 400

@app.route('/api/test-runner/upload-input', methods=['POST'])
def api_upload_input_file():
    """Handle input file upload for the test runner API."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.json'):
        filename = secure_filename(file.filename)
        # Create uploads/test_runner/inputs directory if it doesn't exist
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'test_runner', 'inputs')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # Validate that the file contains valid JSON
        try:
            with open(file_path, 'r') as f:
                json.load(f)
        except json.JSONDecodeError:
            os.remove(file_path)  # Remove invalid file
            return jsonify({'error': 'Invalid JSON file'}), 400

        return jsonify({
            'success': True,
            'filename': filename,
            'path': file_path
        })

    return jsonify({'error': 'File type not allowed. Only JSON files are accepted.'}), 400

@app.route('/api/test-runner/run', methods=['POST'])
def api_run_test():
    """Run a test file with specified configuration."""
    data = request.get_json()
    file_path = data.get('file_path')
    input_mode = data.get('input_mode', 'default')
    input_set = data.get('input_set')
    input_file_path = data.get('input_file_path')
    headless = data.get('headless', False)
    suite_id = data.get('suite_id')

    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Invalid test file path'}), 400
    
    # Create a test run record in the database if suite_id is provided
    test_run = None
    if suite_id:
        test_suite = TestSuite.query.get(suite_id)
        if test_suite:
            test_run = TestRun(
                name=f"Test Run {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                test_suite_id=suite_id,
                status="running"
            )
            db.session.add(test_run)
            db.session.commit()

    try:
        # For default input mode, just run the test file directly
        if input_mode == 'default':
            result = run_test_file(file_path)
            
            # Update test run status if it exists
            if test_run:
                test_run.status = "completed" if result.get('success', False) else "failed"
                db.session.commit()
                
            return jsonify(result)

        # For existing custom input mode, use the test runner script
        elif input_mode == 'existing' and input_set and input_file_path:
            # Check if input file exists
            if not os.path.exists(input_file_path):
                return jsonify({'error': 'Invalid input file path'}), 400

            # Copy the test runner script into the upload directory if it doesn't exist
            from shutil import copyfile
            test_runner_script = os.path.join('features', 'test_runner_app', 'test_runner_script.py')
            dest_script = os.path.join(app.config['UPLOAD_FOLDER'], 'test_runner', 'test_runner_script.py')
            if not os.path.exists(dest_script):
                os.makedirs(os.path.dirname(dest_script), exist_ok=True)
                copyfile(test_runner_script, dest_script)

            # Run the test using the test runner script
            import subprocess
            import sys
            
            cmd = [
                sys.executable,
                dest_script,
                '--test', file_path,
                '--input', input_file_path,
                '--set', input_set
            ]

            if headless:
                cmd.append('--headless')

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            result = {
                'success': proc.returncode == 0,
                'stdout': proc.stdout,
                'stderr': proc.stderr,
                'returncode': proc.returncode
            }
            
            # Update test run status if it exists
            if test_run:
                test_run.status = "completed" if result.get('success', False) else "failed"
                db.session.commit()
                
            return jsonify(result)

        # For dynamic input mode
        else:
            result = run_test_file(file_path)
            
            # Update test run status if it exists
            if test_run:
                test_run.status = "completed" if result.get('success', False) else "failed"
                db.session.commit()
                
            return jsonify(result)

    except subprocess.TimeoutExpired:
        # Update test run status if it exists
        if test_run:
            test_run.status = "failed"
            db.session.commit()
            
        return jsonify({
            'success': False,
            'error': 'Test execution timed out after 5 minutes'
        }), 500
    except Exception as e:
        # Update test run status if it exists
        if test_run:
            test_run.status = "failed"
            db.session.commit()
            
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def run_test_file(file_path):
    """Run a test file using Python and return the results."""
    try:
        import subprocess
        import sys
        
        # Run the test file
        proc = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        return {
            'success': proc.returncode == 0,
            'stdout': proc.stdout,
            'stderr': proc.stderr,
            'returncode': proc.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Test execution timed out after 5 minutes'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# Main entry point
if __name__ == '__main__':
    app.run(debug=True, port=5000)
