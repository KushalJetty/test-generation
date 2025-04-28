def init_test_case_routes(app):
    @app.route('/test-case/<int:case_id>')
    def test_case_detail(case_id):
        """Show test case details."""
        test_case = TestCase.query.get_or_404(case_id)
        if not test_case.is_active:
            flash('This test case has been deleted.', 'error')
            return redirect(url_for('test_suite_detail', suite_id=test_case.test_suite_id))
            
        test_results = TestResult.query.filter_by(test_case_id=case_id, is_active=True).all()
        return render_template('test_case_detail.html', test_case=test_case, test_results=test_results)

    @app.route('/test-case/<int:case_id>/delete', methods=['POST'])
    def delete_test_case(case_id):
        """Soft delete a test case."""
        test_case = TestCase.query.get_or_404(case_id)
        test_case.is_active = False
        
        # Also soft delete all related test results
        TestResult.query.filter_by(test_case_id=case_id).update({'is_active': False})
        
        db.session.commit()
        
        flash('Test case deleted successfully!', 'success')
        return redirect(url_for('test_suite_detail', suite_id=test_case.test_suite_id)) 