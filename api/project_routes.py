from flask import render_template, request, redirect, url_for, flash
from models import db, Project, TestSuite
from forms import ProjectForm

def init_project_routes(app):
    @app.route('/projects')
    def projects():
        """List all active projects."""
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
        if not project.active:
            flash('This project has been deleted.', 'error')
            return redirect(url_for('projects'))
            
        test_suites = project.test_suites
        
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
        """Soft delete a project."""
        project = Project.query.get_or_404(project_id)
        project.active = False
        db.session.commit()
        
        flash('Project deleted successfully!', 'success')
        return redirect(url_for('projects'))