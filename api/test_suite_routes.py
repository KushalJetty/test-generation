from flask import render_template, request, redirect, url_for, flash
from models import db, Project, TestSuite, TestCase, TestResult, TestRun
from forms import TestSuiteForm
from streamzai_test_generator import StreamzAITestGenerator
import os
import re

def init_test_suite_routes(app):
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
        form.project_id.choices = [(p.id, p.name) for p in Project.query.filter_by(active=True).order_by(Project.name).all()]
        
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
            
            project = Project.query.get(form.project_id.data)
            generator = StreamzAITestGenerator()
            
            ignore_patterns = []
            if form.ignore_patterns.data is not None:
                ignore_patterns = [p.strip() for p in form.ignore_patterns.data.split('\n') if p.strip()]
            if ignore_patterns:
                generator.ignore_patterns = [f"^{re.escape(p)}$" for p in ignore_patterns]
            
            supported_files = generator.traverse_directory(project.path)
            
            for file_path in supported_files:
                test_case = TestCase(
                    original_file_path=file_path,
                    test_file_path=f"{file_path}_test",
                    language="python",
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
        if not test_suite.active:
            flash('This test suite has been deleted.', 'error')
            return redirect(url_for('test_suites'))
            
        test_cases = TestCase.query.filter_by(test_suite_id=suite_id, active=True).all()
        test_runs = TestRun.query.filter_by(test_suite_id=suite_id, active=True).all()
        return render_template('test_suite_detail.html', test_suite=test_suite, test_cases=test_cases, test_runs=test_runs)

    @app.route('/test-suite/<int:suite_id>/edit', methods=['GET', 'POST'])
    def edit_test_suite(suite_id):
        """Edit an existing test suite."""
        test_suite = TestSuite.query.get_or_404(suite_id)
        if not test_suite.active:
            flash('This test suite has been deleted.', 'error')
            return redirect(url_for('test_suites'))
            
        form = TestSuiteForm(obj=test_suite)
        form.project_id.choices = [(p.id, p.name) for p in Project.query.filter_by(active=True).order_by(Project.name).all()]
        
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
        """Soft delete a test suite."""
        test_suite = TestSuite.query.get_or_404(suite_id)
        test_suite.active = False
        
        # Also soft delete all related test cases and test runs
        TestCase.query.filter_by(test_suite_id=suite_id).update({'active': False})
        TestRun.query.filter_by(test_suite_id=suite_id).update({'active': False})
        
        db.session.commit()
        
        flash('Test suite deleted successfully!', 'success')
        return redirect(url_for('test_suites'))