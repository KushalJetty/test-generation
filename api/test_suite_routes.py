from flask import render_template, request, redirect, url_for, flash
from models import db, Project, TestSuite, TestCase, TestResult
from forms import TestSuiteForm
from streamzai_test_generator import StreamzAITestGenerator
import os
import re

def init_test_suite_routes(app):
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
        form.project_id.choices = [(p.id, p.name) for p in Project.query.order_by(Project.name).all()]
        
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
                file_analysis = generator.analyze_file(file_path)
                test_case_result = generator.generate_test_case(file_analysis)
                
                if "error" not in test_case_result:
                    rel_path = os.path.relpath(file_path, start=project.path)
                    file_name = os.path.basename(file_path)
                    file_base, file_ext = os.path.splitext(file_name)
                    
                    language = file_analysis["language"]
                    test_file_name = f"test_{file_base}{file_ext}" if language == "python" else f"{file_base}.test{file_ext}"
                    
                    rel_dir = os.path.dirname(rel_path)
                    test_dir = os.path.join("generated_tests", project.name, rel_dir)
                    os.makedirs(test_dir, exist_ok=True)
                    
                    test_file_path = os.path.join(test_dir, test_file_name)
                    with open(test_file_path, 'w', encoding='utf-8') as f:
                        f.write(test_case_result["test_content"])
                    
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