import datetime
from models import db, TestRun, TestCase, TestResult
from streamzai_test_generator import logger
import os

# Global variable to track active test runs
active_test_runs = {}

def run_tests_async(test_run_id):
    """Run tests asynchronously for a test run.
    
    Args:
        test_run_id: ID of the test run to execute
    """
    from flask import current_app
    with current_app.app_context():
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