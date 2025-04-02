import os
import json
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environment
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from models import db, Project, TestSuite, TestCase, TestRun, TestResult
from forms import ProjectForm, TestSuiteForm, TestRunForm, FilterForm, ExportForm
from streamzai_test_generator import StreamzAITestGenerator, logger
import threading
import uuid
import io
import re

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'streamzai-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///streamzai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

# Global variables
active_test_runs = {}
recording_actions = []
is_recording = False

# Helper functions
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
            from test_runner import StreamzAITestRunner
            
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

@app.route('/test-suite/<int:suite_id>/generate', methods=['GET'])
def generate_test_cases(suite_id):
    """Generate test cases for a test suite."""
    test_suite = TestSuite.query.get_or_404(suite_id)
    project = test_suite.project
    
    # Create a generator instance
    generator = StreamzAITestGenerator()
    
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
    flash('Test cases generated successfully!', 'success')
    return redirect(url_for('test_suite_detail', suite_id=test_suite.id))

@app.route('/api/record/start', methods=['POST'])
def start_recording():
    """Start recording browser actions."""
    global is_recording, recording_actions
    data = request.get_json()
    suite_id = data.get('suite_id')
    
    # Clear previous actions and start recording
    recording_actions = []
    is_recording = True
    
    return jsonify({
        'status': 'success',
        'message': 'Recording started'
    })

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
    recording_actions.append(action)
    
    return jsonify({
        'status': 'success',
        'message': 'Action recorded'
    })

@app.route('/api/record/stop', methods=['POST'])
def stop_recording():
    """Stop recording and generate Selenium code."""
    global is_recording, recording_actions
    is_recording = False
    
    # Generate Selenium code from recorded actions
    selenium_code = generate_selenium_code(recording_actions)
    
    # Create test cases from recorded actions
    test_cases = generate_test_cases_from_actions(recording_actions)
    
    # Clear recorded actions
    recording_actions = []
    
    return jsonify({
        'status': 'success',
        'selenium_code': selenium_code,
        'test_cases': test_cases
    })

def generate_selenium_code(actions):
    """Generate Selenium code from recorded actions."""
    code = [
        "from selenium import webdriver",
        "from selenium.webdriver.common.by import By",
        "from selenium.webdriver.support.ui import WebDriverWait",
        "from selenium.webdriver.support import expected_conditions as EC",
        "",
        "def test_recorded_actions():",
        "    # Initialize the driver",
        "    driver = webdriver.Chrome()",
        "    wait = WebDriverWait(driver, 10)",
        ""
    ]
    
    for action in actions:
        if action['type'] == 'click':
            code.append(f"    # Click on element {action['selector']}")
            code.append(f"    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '{action['selector']}'))).click()")
        elif action['type'] == 'input':
            code.append(f"    # Input text into {action['selector']}")
            code.append(f"    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '{action['selector']}')))")
            code.append(f"    element.send_keys('{action['value']}')")
        elif action['type'] == 'navigate':
            code.append(f"    # Navigate to {action['url']}")
            code.append(f"    driver.get('{action['url']}')")
    
    code.extend([
        "",
        "    # Close the browser",
        "    driver.quit()"
    ])
    
    return "\n".join(code)

def generate_test_cases_from_actions(actions):
    """Generate test cases from recorded actions."""
    test_cases = []
    current_test = {
        'name': 'Recorded Test Case',
        'description': 'Test case generated from recorded browser actions',
        'steps': []
    }
    
    for action in actions:
        if action['type'] == 'click':
            current_test['steps'].append(f"Click on element {action['selector']}")
        elif action['type'] == 'input':
            current_test['steps'].append(f"Enter '{action['value']}' into {action['selector']}")
        elif action['type'] == 'navigate':
            current_test['steps'].append(f"Navigate to {action['url']}")
    
    test_cases.append(current_test)
    return test_cases

# Main entry point
if __name__ == '__main__':
    app.run(debug=True, port=5000)