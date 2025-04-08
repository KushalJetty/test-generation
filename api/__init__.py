from flask import render_template
from models import Project, TestSuite, TestRun, TestResult
from chart_utils import generate_chart
from .project_routes import init_project_routes
from .test_suite_routes import init_test_suite_routes
from .test_run_routes import init_test_run_routes
from .report_routes import init_report_routes

def init_routes(app):
    """Initialize all route modules and register the dashboard route."""
    
    @app.route('/')
    def index():
        """Dashboard home page."""
        projects_count = Project.query.count()
        test_suites_count = TestSuite.query.count()
        test_runs_count = TestRun.query.count()
        
        passed_results = TestResult.query.filter_by(status='passed').count()
        total_results = TestResult.query.count()
        success_rate = round((passed_results / total_results) * 100) if total_results > 0 else 0
        
        recent_test_runs = TestRun.query.order_by(TestRun.created_at.desc()).limit(5).all()
        recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
        
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
    
    # Initialize all route modules
    init_project_routes(app)
    init_test_suite_routes(app)
    init_test_run_routes(app)
    init_report_routes(app)