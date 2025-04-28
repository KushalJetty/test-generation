from flask import render_template, request, redirect, url_for, flash
from models import db, TestSuite, TestRun, TestResult
from forms import TestRunForm
from folder_analyser.test_executor import run_tests_async, active_test_runs
from chart_utils import generate_chart
import threading

def init_test_run_routes(app):
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
        form.test_suite_id.choices = [(ts.id, f"{ts.name} ({ts.project.name})") for ts in TestSuite.query.join(Project).order_by(TestSuite.name).all()]
        
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
            
            thread = threading.Thread(target=run_tests_async, args=(test_run.id,))
            thread.daemon = True
            thread.start()
            
            active_test_runs[test_run.id] = thread
            
            flash('Test run started!', 'success')
            return redirect(url_for('test_run_detail', run_id=test_run.id))
        
        return render_template('test_run_form.html', form=form, title='Create Test Run')

    @app.route('/test-run/<int:run_id>')
    def test_run_detail(run_id):
        """Show test run details."""
        test_run = TestRun.query.get_or_404(run_id)
        
        if not test_run.active:
            flash('This test run has been deleted.', 'error')
            return redirect(url_for('test_suite_detail', suite_id=test_run.test_suite_id))
            
        test_results = TestResult.query.filter_by(test_run_id=run_id, active=True).all()
        
        summary = {
            'passed': TestResult.query.filter_by(test_run_id=run_id, status='passed').count(),
            'failed': TestResult.query.filter_by(test_run_id=run_id, status='failed').count(),
            'skipped': TestResult.query.filter_by(test_run_id=run_id, status='skipped').count(),
            'error': TestResult.query.filter_by(test_run_id=run_id, status='error').count()
        }
        summary['total'] = sum(summary.values())
        
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

    @app.route('/test-run/<int:run_id>/delete', methods=['POST'])
    def delete_test_run(run_id):
        """Soft delete a test run."""
        test_run = TestRun.query.get_or_404(run_id)
        test_run.active = False
        db.session.commit()
        
        # Also soft delete all related test results
        TestResult.query.filter_by(test_run_id=run_id).update({'active': False})
        db.session.commit()
        
        flash('Test run deleted successfully!', 'success')
        return redirect(url_for('test_suite_detail', suite_id=test_run.test_suite_id))