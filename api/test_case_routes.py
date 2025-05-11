import os
import sys
import subprocess
import threading
import time
from datetime import datetime

def init_test_case_routes(app):
    @app.route('/test-case/<int:case_id>')
    def test_case_detail(case_id):
        """Show test case details."""
        test_case = TestCase.query.get_or_404(case_id)
        
        if not test_case.active:
            flash('This test case has been deleted.', 'error')
            return redirect(url_for('test_suite_detail', suite_id=test_case.test_suite_id))
            
        test_results = TestResult.query.filter_by(test_case_id=case_id, active=True).all()
        
        return render_template('test_case_detail.html', test_case=test_case, test_results=test_results)

    @app.route('/test-case/<int:case_id>/delete', methods=['POST'])
    def delete_test_case(case_id):
        """Soft delete a test case."""
        test_case = TestCase.query.get_or_404(case_id)
        test_case.active = False
        db.session.commit()
        
        # Also soft delete all related test results
        TestResult.query.filter_by(test_case_id=case_id).update({'active': False})
        db.session.commit()
        
        flash('Test case deleted successfully!', 'success')
        return redirect(url_for('test_suite_detail', suite_id=test_case.test_suite_id))

    @app.route('/api/test-case/<int:case_id>/run', methods=['POST'])
    def run_test_case(case_id):
        """Run a specific test case."""
        try:
            test_case = TestCase.query.get_or_404(case_id)
            
            # Create a new test run for this single test case
            test_run = TestRun(
                name=f"Run of {test_case.name}",
                status="running",
                start_time=datetime.utcnow(),
                test_suite_id=test_case.test_suite_id
            )
            db.session.add(test_run)
            db.session.commit()
            
            # Create a test result entry
            test_result = TestResult(
                test_case_id=test_case.id,
                test_run_id=test_run.id,
                status="running"
            )
            db.session.add(test_result)
            db.session.commit()
            
            # Start test execution in a background thread
            thread = threading.Thread(
                target=execute_single_test_case,
                args=(test_case.id, test_run.id, test_result.id)
            )
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'status': 'success',
                'message': 'Test execution started',
                'test_run_id': test_run.id
            })
        except Exception as e:
            return jsonify({'status': 'error', 'error': str(e)}), 500

    def execute_single_test_case(test_case_id, test_run_id, test_result_id):
        """Execute a single test case in a separate thread."""
        with app.app_context():
            try:
                test_case = TestCase.query.get(test_case_id)
                test_result = TestResult.query.get(test_result_id)
                test_run = TestRun.query.get(test_run_id)
                
                if not test_case or not test_result or not test_run:
                    raise Exception("Test case, result or run not found")
                
                # Check if the test file exists
                if not os.path.exists(test_case.test_file_path):
                    test_result.status = "error"
                    test_result.error_message = f"Test file not found: {test_case.test_file_path}"
                    test_run.status = "failed"
                    test_run.end_time = datetime.utcnow()
                    db.session.commit()
                    return
                
                # Execute the test file
                start_time = time.time()
                result = None
                error_message = None
                
                try:
                    # Run the Python file as a subprocess
                    process = subprocess.Popen(
                        [sys.executable, test_case.test_file_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
                    
                    if process.returncode == 0:
                        result = "passed"
                    else:
                        result = "failed"
                        error_message = stderr or "Test execution failed with no error message"
                except subprocess.TimeoutExpired:
                    process.kill()
                    result = "failed"
                    error_message = "Test execution timed out after 5 minutes"
                except Exception as e:
                    result = "error"
                    error_message = str(e)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Update test result
                test_result.status = result
                test_result.execution_time = execution_time
                if error_message:
                    test_result.error_message = error_message
                
                # Update test run
                test_run.end_time = datetime.utcnow()
                test_run.status = "completed" if result == "passed" else "failed"
                
                db.session.commit()
                
            except Exception as e:
                # Log the error
                print(f"Error executing test case {test_case_id}: {str(e)}")
                
                # Update test result and run with error status
                try:
                    test_result = TestResult.query.get(test_result_id)
                    if test_result:
                        test_result.status = "error"
                        test_result.error_message = str(e)
                    
                    test_run = TestRun.query.get(test_run_id)
                    if test_run:
                        test_run.status = "failed"
                        test_run.end_time = datetime.utcnow()
                    
                    db.session.commit()
                except Exception as inner_e:
                    print(f"Error updating test result: {str(inner_e)}")
