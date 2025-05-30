from flask import render_template, redirect, url_for, flash
from models import db, TestResult
from forms import FilterForm, ExportForm

def init_report_routes(app):
    @app.route('/reports')
    def reports():
        """Show test reports."""
        filter_form = FilterForm()
        export_form = ExportForm()
        
        # Query test results based on filters
        query = TestResult.query
        
        if filter_form.status.data:
            query = query.filter_by(status=filter_form.status.data)
        if filter_form.date_from.data:
            query = query.filter(TestResult.created_at >= filter_form.date_from.data)
        if filter_form.date_to.data:
            query = query.filter(TestResult.created_at <= filter_form.date_to.data)
        
        results = query.all()
        
        summary = {
            'total': len(results),
            'passed': sum(1 for r in results if r.status == 'passed'),
            'failed': sum(1 for r in results if r.status == 'failed'),
            'skipped': sum(1 for r in results if r.status == 'skipped'),
            'error': sum(1 for r in results if r.status == 'error')
        }
        
        return render_template('reports.html', 
                           filter_form=filter_form, 
                           export_form=export_form,
                           results=results,
                           summary=summary)

    @app.route('/export-results', methods=['POST'])
    def export_results():
        """Export test results in the specified format."""
        form = ExportForm()
        if form.validate_on_submit():
            # Query test results
            query = TestResult.query
            
            if form.test_run_id.data:
                query = query.filter_by(test_run_id=form.test_run_id.data)
            if form.test_suite_id.data:
                query = query.filter_by(test_suite_id=form.test_suite_id.data)
            
            results = query.all()
            
            # TODO: Implement actual export logic based on form.format.data
            flash('Export functionality will be implemented soon!', 'info')
            return redirect(url_for('reports'))
        
        flash('Invalid export parameters!', 'error')
        return redirect(url_for('reports'))