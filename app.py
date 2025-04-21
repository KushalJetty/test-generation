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
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from models import db, Project, TestSuite, TestCase, TestRun, TestResult
from forms import ProjectForm, TestSuiteForm, TestRunForm, FilterForm, ExportForm, TestExecutionForm
import threading
import uuid
import io
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from generate_code.selenium_code_generator import generate_test_file
from playwright.async_api import async_playwright
import asyncio

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'streamzai-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///streamzai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
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
    'awaiting_input': None
}
recording_actions = []
is_recording = False
driver = None

@app.route('/test-case/upload', methods=['GET', 'POST'])
def upload_test_case():
    """Handle test case file upload."""
    form = TestExecutionForm()
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if file and file.filename.endswith('.json'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
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
    
    # Handle GET request
    return render_template('test_run_form.html', form=form)

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
        return jsonify({'awaiting': True, 'var_name': var_name})
    return jsonify({'awaiting': False})

@app.route('/test-case/submit_input', methods=['POST'])
def submit_input():
    """Submit input for test execution."""
    data = request.json
    value = data.get('value')
    execution_state['input_queue'].put(value)
    return jsonify({'success': True})

def log_message(msg):
    execution_state['log'].append(msg)

def execute_test_case():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Keep browser visible
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Navigate to the target URL
            page.goto(execution_state['target_url'])
            log_message(f"Navigated to {execution_state['target_url']}")
            
            # Wait for page load
            page.wait_for_load_state('networkidle')
            
            # Execute each test step
            for idx, step in enumerate(execution_state['test_steps']):
                if not execution_state['running']:
                    break
                    
                while execution_state['paused']:
                    continue
                    
                execution_state['current_step'] = idx
                log_message(f"Executing step {idx + 1}")
                
                # Get step details
                action = step.get('action', '')
                selector = step.get('selector', '')
                value = step.get('value', '')
                
                try:
                    # Wait for element to be visible before any action
                    if selector:
                        page.wait_for_selector(selector, state='visible', timeout=10000)
                    
                    if action == 'click':
                        # For login button, wait for navigation after click
                        if 'signin-btn' in selector:
                            with page.expect_navigation():
                                page.click(selector)
                            log_message("Clicked login button and waiting for navigation")
                        else:
                            page.click(selector)
                            log_message(f"Clicked element: {selector}")
                        
                    elif action == 'fill' or action == 'input':
                        if value.startswith('{') and value.endswith('}'):
                            var_name = value[1:-1]
                            execution_state['awaiting_input'] = var_name
                            log_message(f"Waiting for user input for {var_name}...")
                            
                            # Wait for input from the queue
                            input_value = execution_state['input_queue'].get()
                            if input_value is None:
                                log_message("User cancelled input")
                                break
                                
                            value = input_value
                            execution_state['awaiting_input'] = None
                            
                        # For password field, use type instead of fill for security
                        if 'Password' in selector:
                            page.type(selector, value, delay=100)
                            log_message("Entered password")
                        else:
                            page.fill(selector, value)
                            log_message(f"Filled {selector} with value")
                        
                    elif action == 'wait':
                        wait_time = int(value) if value else 1000
                        page.wait_for_timeout(wait_time)
                        log_message(f"Waited for {wait_time}ms")
                        
                    elif action == 'navigate':
                        page.goto(value)
                        log_message(f"Navigated to: {value}")
                        page.wait_for_load_state('networkidle')
                    
                    # Add delay between steps
                    page.wait_for_timeout(1000)
                    
                except Exception as e:
                    log_message(f"Error in step {idx + 1}: {str(e)}")
                    continue
            
            log_message("All test steps completed")
            
        except Exception as e:
            log_message(f"Error during test execution: {str(e)}")
        finally:
            if not execution_state['awaiting_input']:
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
    projects = Project.query.order_by(Project.name).all()
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
    test_suites = project.test_suites
    
    # Get test statistics for this project
    test_stats = {}
    for test_suite in test_suites:
        for test_run in test_suite.test_runs:
            passed = TestResult.query.filter_by(test_run_id=test_run.id, status='passed').count()
            failed = TestResult.query.filter_by(test_run_id=test_run.id, status='failed').count()
            skipped = TestResult.query.filter_by(test_run_id=test_run.id, status='skipped').count()
            error = TestResult.query.filter_by(test_run_id=test_run.id, status='error').count()
            
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
    test_suites = TestSuite.query.order_by(TestSuite.name).all()
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
        test_suite = TestSuite(
            name=form.name.data,
            description=form.description.data,
            project_id=form.project_id.data
        )
        db.session.add(test_suite)
        db.session.commit()
        
        # Generate test cases for this test suite
        project = Project.query.get(form.project_id.data)
        
        # Create a generator instance
        generator = StreamzAITestGenerator()
        
        # Get ignore patterns from form
        ignore_patterns = []
        if form.ignore_patterns.data is not None:
            ignore_patterns = [p.strip() for p in form.ignore_patterns.data.split('\n') if p.strip()]
        if ignore_patterns:
            generator.ignore_patterns = [f"^{re.escape(p)}$" for p in ignore_patterns]
        
        # Find all supported files
        supported_files = generator.traverse_directory(project.path)
        
        # Generate test cases for each file
        for file_path in supported_files:
            # Analyze file
            file_analysis = generator.analyze_file(file_path)
            
            # Generate test case
            test_case_result = generator.generate_test_case(file_analysis)
            
            if "error" not in test_case_result:
                # Create test case in database
                rel_path = os.path.relpath(file_path, start=project.path)
                file_name = os.path.basename(file_path)
                file_base, file_ext = os.path.splitext(file_name)
                
                # Create appropriate test file name based on language
                language = file_analysis["language"]
                if language == "python":
                    test_file_name = f"test_{file_base}{file_ext}"
                else:
                    test_file_name = f"{file_base}.test{file_ext}"
                
                # Create directory structure in output directory
                rel_dir = os.path.dirname(rel_path)
                test_dir = os.path.join("generated_tests", project.name, rel_dir)
                os.makedirs(test_dir, exist_ok=True)
                
                # Save test content to file
                test_file_path = os.path.join(test_dir, test_file_name)
                with open(test_file_path, 'w', encoding='utf-8') as f:
                    f.write(test_case_result["test_content"])
                
                # Create test case in database
                test_case = TestCase(
                    original_file_path=file_path,
                    test_file_path=test_file_path,
                    language=language,
                    test_suite_id=test_suite.id
                )
                db.session.add(test_case)
        
        db.session.commit()
        
        flash('Test suite created successfully!', 'success')
        return redirect(url_for('test_suite_detail', suite_id=test_suite.id))
    
    return render_template('test_suite_form.html', form=form, title='Create Test Suite')

@app.route('/test-suite/<int:suite_id>')
def test_suite_detail(suite_id):
    """Show test suite details."""
    test_suite = TestSuite.query.get_or_404(suite_id)
    test_cases = test_suite.test_cases
    test_runs = test_suite.test_runs
    
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
    test_runs = TestRun.query.order_by(TestRun.created_at.desc()).all()
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
    test_results = TestResult.query.filter_by(test_run_id=test_run.id).all()
    
    # Calculate summary
    summary = {
        'passed': TestResult.query.filter_by(test_run_id=test_run.id, status='passed').count(),
        'failed': TestResult.query.filter_by(test_run_id=test_run.id, status='failed').count(),
        'skipped': TestResult.query.filter_by(test_run_id=test_run.id, status='skipped').count(),
        'error': TestResult.query.filter_by(test_run_id=test_run.id, status='error').count()
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
def start_recording():
    """Start recording browser actions."""
    global is_recording, recording_actions, driver
    data = request.get_json()
    suite_id = data.get('suite_id')
    url = data.get('url', 'https://test.teamstreamz.com/')
    
    try:
        # Initialize Chrome driver with appropriate options
        chrome_options = Options()
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-extensions')  # Disable extensions that might interfere
        chrome_options.add_argument('--disable-popup-blocking')  # Allow popups
        chrome_options.add_argument('--disable-infobars')  # Disable infobars
        chrome_options.add_argument('--disable-notifications')  # Disable notifications
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])  # Disable automation info bar
        chrome_options.add_experimental_option('useAutomationExtension', False)  # Disable automation extension
        
        driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to the specified URL
        driver.get(url)
        
        # Clear previous actions and start recording
        recording_actions = []
        is_recording = True
        
        # Inject the recorder script into the browser
        recorder_script = """
        window.recordingActions = [];
        
        function recordAction(action) {
            window.recordingActions.push(action);
            fetch('/api/record/action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(action)
            }).catch(error => console.error('Failed to record action:', error));
        }
        
        // Set up event listeners
        document.addEventListener('click', function(event) {
            const element = event.target;
            const selector = getSelector(element);
            if (selector) {
                recordAction({
                    type: 'click',
                    selector: selector,
                    description: 'Clicked on ' + element.tagName.toLowerCase() + (element.id ? '#' + element.id : '')
                });
            }
        }, true);
        
        document.addEventListener('input', function(event) {
            const element = event.target;
            const selector = getSelector(element);
            if (selector) {
                recordAction({
                    type: 'input',
                    selector: selector,
                    value: element.value,
                    description: 'Entered text in ' + element.tagName.toLowerCase() + (element.id ? '#' + element.id : '')
                });
            }
        }, true);
        
        document.addEventListener('submit', function(event) {
            const form = event.target;
            const selector = getSelector(form);
            if (selector) {
                recordAction({
                    type: 'submit',
                    selector: selector,
                    description: 'Submitted form' + (form.id ? ' #' + form.id : '')
                });
            }
        }, true);
        
        document.addEventListener('keydown', function(event) {
            const specialKeys = ['Enter', 'Tab', 'Escape'];
            if (specialKeys.includes(event.key)) {
                recordAction({
                    type: 'keypress',
                    key: event.key,
                    description: 'Pressed ' + event.key + ' key'
                });
            }
        }, true);
        
        function getSelector(element) {
            if (!element) return null;
            
            // Try ID first
            if (element.id) {
                return '#' + element.id;
            }
            
            // Try name attribute
            if (element.name) {
                return '[name="' + element.name + '"]';
            }
            
            // Try data attributes
            const dataAttrs = Array.from(element.attributes)
                .filter(attr => attr.name.startsWith('data-'));
            if (dataAttrs.length > 0) {
                return '[' + dataAttrs[0].name + '="' + dataAttrs[0].value + '"]';
            }
            
            // Try type and name combination for inputs
            if (element.type && element.name) {
                return 'input[type="' + element.type + '"][name="' + element.name + '"]';
            }
            
            // Try classes
            if (element.className) {
                const classes = Array.from(element.classList)
                    .filter(cls => !cls.includes(' '))
                    .join('.');
                if (classes) {
                    const similar = document.querySelectorAll('.' + classes);
                    if (similar.length === 1) {
                        return '.' + classes;
                    }
                }
            }
            
            // Try parent context with nth-child
            let path = [];
            let current = element;
            
            while (current && current !== document.body) {
                let selector = current.tagName.toLowerCase();
                let parent = current.parentElement;
                
                if (parent) {
                    let children = Array.from(parent.children);
                    let index = children.filter(child => child.tagName === current.tagName).indexOf(current);
                    if (index > 0) {
                        selector += ':nth-of-type(' + (index + 1) + ')';
                    }
                }
                
                path.unshift(selector);
                current = parent;
            }
            
            return path.join(' > ');
        }
        
        console.log('Recorder script injected successfully');
        """
        
        # Execute the script in the browser
        driver.execute_script(recorder_script)
        
        return jsonify({
            'status': 'success',
            'message': 'Recording started'
        })
    except Exception as e:
        if driver:
            driver.quit()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/record/action', methods=['POST'])
def record_action():
    """Record a browser action."""
    global recording_actions
    if not is_recording:
        return jsonify({
            'status': 'error',
            'message': 'Not currently recording'
        })
    
    action = request.get_json()
    action['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    recording_actions.append(action)
    
    # Log the action for debugging
    print(f"Recorded action: {action}")
    
    return jsonify({
        'status': 'success',
        'message': 'Action recorded'
    })

@app.route('/api/record/stop', methods=['POST'])
def stop_recording():
    """Stop recording and generate Selenium code."""
    global is_recording, recording_actions, driver
    is_recording = False
    
    try:
        # Get recorded actions from the browser
        if driver:
            # Execute script to get recorded actions
            browser_actions = driver.execute_script("return window.recordingActions || [];")
            
            # Add browser actions to our recording_actions list
            if browser_actions:
                for action in browser_actions:
                    action['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    recording_actions.append(action)
            
            # Close the browser
            driver.quit()
            driver = None
        
        # Generate test file
        test_file = generate_test_file(recording_actions)
        
        # Read the generated code
        with open(test_file, 'r', encoding='utf-8') as f:
            selenium_code = f.read()
        
        # Create test cases from recorded actions
        test_cases = generate_test_cases_from_actions(recording_actions)
        
        # Prepare response with recorded actions
        response = {
            'status': 'success',
            'selenium_code': selenium_code,
            'test_cases': test_cases,
            'actions': [{
                'timestamp': action.get('timestamp', ''),
                'description': action.get('description', ''),
                'type': action.get('type', ''),
                'selector': action.get('selector', ''),
                'value': action.get('value', '')
            } for action in recording_actions]
        }
        
        # Clear recorded actions
        recording_actions = []
        
        return jsonify(response)
    except Exception as e:
        if driver:
            driver.quit()
            driver = None
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def generate_test_cases_from_actions(actions):
    """Generate test cases from recorded actions."""
    test_cases = []
    current_test = {
        'name': 'Recorded Test Case',
        'description': 'Test case generated from recorded browser actions',
        'steps': []
    }
    
    for action in actions:
        description = None
        if action['type'] == 'click':
            description = f"Click on element {action['selector']}"
        elif action['type'] == 'input':
            description = f"Enter '{action['value']}' into {action['selector']}"
        elif action['type'] == 'navigate':
            description = f"Navigate to {action['url']}"
        elif action['type'] == 'keypress':
            description = f"Press {action['key']} key"
            
        if description:
            current_test['steps'].append(description)
    
    test_cases.append(current_test)
    return test_cases

# Main entry point
if __name__ == '__main__':
    app.run(debug=True, port=5000)
