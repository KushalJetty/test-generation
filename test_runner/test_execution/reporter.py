import os
import json
import time
import pandas as pd
from datetime import datetime

class TestReporter:
    """
    Records and reports test execution results.
    """
    
    def __init__(self):
        """
        Initialize the test reporter.
        """
        self.start_time = time.time()
        self.end_time = None
        self.steps = []
        self.network_requests = []
        self.network_responses = []
        self.console_messages = []
        self.screenshots = []
        self.failures = []
        self.warnings = []
    
    def record_step(self, step, status, error=None, duration=None):
        """
        Record a test step.
        
        Args:
            step (dict): The test step
            status (str): Step status ('success', 'failure', 'warning')
            error (str, optional): Error message if status is 'failure'
            duration (float, optional): Step duration in seconds
        """
        self.steps.append({
            'step': step,
            'status': status,
            'error': error,
            'duration': duration,
            'timestamp': time.time()
        })
        
        if status == 'failure':
            self.failures.append({
                'step': step,
                'error': error,
                'timestamp': time.time()
            })
        elif status == 'warning':
            self.warnings.append({
                'step': step,
                'error': error,
                'timestamp': time.time()
            })
    
    def record_network_request(self, request):
        """
        Record a network request.
        
        Args:
            request: Playwright request object
        """
        self.network_requests.append({
            'url': request.url,
            'method': request.method,
            'headers': request.headers,
            'timestamp': time.time()
        })
    
    def record_network_response(self, response):
        """
        Record a network response.
        
        Args:
            response: Playwright response object
        """
        self.network_responses.append({
            'url': response.url,
            'status': response.status,
            'headers': response.headers,
            'timestamp': time.time()
        })
    
    def record_console_message(self, message_type, text):
        """
        Record a console message.
        
        Args:
            message_type (str): Message type ('log', 'error', 'warning', etc.)
            text (str): Message text
        """
        self.console_messages.append({
            'type': message_type,
            'text': text,
            'timestamp': time.time()
        })
    
    def record_screenshot(self, path):
        """
        Record a screenshot.
        
        Args:
            path (str): Path to the screenshot file
        """
        self.screenshots.append({
            'path': path,
            'timestamp': time.time()
        })
    
    def has_failures(self):
        """
        Check if there are any failures.
        
        Returns:
            bool: True if there are failures, False otherwise
        """
        return len(self.failures) > 0
    
    def has_warnings(self):
        """
        Check if there are any warnings.
        
        Returns:
            bool: True if there are warnings, False otherwise
        """
        return len(self.warnings) > 0
    
    def get_summary(self):
        """
        Get a summary of the test execution.
        
        Returns:
            dict: Test execution summary
        """
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': duration,
            'total_steps': len(self.steps),
            'successful_steps': sum(1 for step in self.steps if step['status'] == 'success'),
            'failed_steps': sum(1 for step in self.steps if step['status'] == 'failure'),
            'warning_steps': sum(1 for step in self.steps if step['status'] == 'warning'),
            'network_requests': len(self.network_requests),
            'network_responses': len(self.network_responses),
            'console_messages': len(self.console_messages),
            'screenshots': len(self.screenshots)
        }
    
    def get_report_data(self):
        """
        Get the report data.
        
        Returns:
            dict: Report data
        """
        return {
            'summary': self.get_summary(),
            'steps': self.steps,
            'failures': self.failures,
            'warnings': self.warnings,
            'network_requests': self.network_requests,
            'network_responses': self.network_responses,
            'console_messages': self.console_messages,
            'screenshots': self.screenshots
        }

def generate_report(reporter, format='json'):
    """
    Generate a test report.
    
    Args:
        reporter (TestReporter): The test reporter
        format (str): Report format ('json', 'html', 'csv', 'excel')
        
    Returns:
        str: Path to the generated report
    """
    # Ensure reports directory exists
    os.makedirs(os.path.join('test_runner', 'reports'), exist_ok=True)
    
    # Generate report filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format == 'json':
        # Generate JSON report
        report_path = os.path.join('test_runner', 'reports', f'report_{timestamp}.json')
        with open(report_path, 'w') as f:
            json.dump(reporter.get_report_data(), f, indent=2)
    elif format == 'html':
        # Generate HTML report
        report_path = os.path.join('test_runner', 'reports', f'report_{timestamp}.html')
        _generate_html_report(reporter, report_path)
    elif format == 'csv':
        # Generate CSV report
        report_path = os.path.join('test_runner', 'reports', f'report_{timestamp}.csv')
        _generate_csv_report(reporter, report_path)
    elif format == 'excel':
        # Generate Excel report
        report_path = os.path.join('test_runner', 'reports', f'report_{timestamp}.xlsx')
        _generate_excel_report(reporter, report_path)
    else:
        # Default to JSON
        report_path = os.path.join('test_runner', 'reports', f'report_{timestamp}.json')
        with open(report_path, 'w') as f:
            json.dump(reporter.get_report_data(), f, indent=2)
    
    return report_path

def _generate_html_report(reporter, report_path):
    """
    Generate an HTML report.
    
    Args:
        reporter (TestReporter): The test reporter
        report_path (str): Path to save the report
    """
    summary = reporter.get_summary()
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Execution Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .summary-item {{ margin-bottom: 10px; }}
            .step {{ margin-bottom: 10px; padding: 10px; border-left: 5px solid #ccc; }}
            .step.success {{ border-left-color: #4CAF50; }}
            .step.failure {{ border-left-color: #F44336; }}
            .step.warning {{ border-left-color: #FFC107; }}
            .failure {{ color: #F44336; }}
            .warning {{ color: #FFC107; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1>Test Execution Report</h1>
        <div class="summary">
            <h2>Summary</h2>
            <div class="summary-item">Start Time: {datetime.fromtimestamp(summary['start_time']).strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div class="summary-item">End Time: {datetime.fromtimestamp(summary['end_time']).strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div class="summary-item">Duration: {summary['duration']:.2f} seconds</div>
            <div class="summary-item">Total Steps: {summary['total_steps']}</div>
            <div class="summary-item">Successful Steps: {summary['successful_steps']}</div>
            <div class="summary-item">Failed Steps: {summary['failed_steps']}</div>
            <div class="summary-item">Warning Steps: {summary['warning_steps']}</div>
            <div class="summary-item">Network Requests: {summary['network_requests']}</div>
            <div class="summary-item">Network Responses: {summary['network_responses']}</div>
            <div class="summary-item">Console Messages: {summary['console_messages']}</div>
            <div class="summary-item">Screenshots: {summary['screenshots']}</div>
        </div>
        
        <h2>Test Steps</h2>
        <table>
            <tr>
                <th>Action</th>
                <th>Selector</th>
                <th>Value</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Error</th>
            </tr>
    """
    
    for step in reporter.steps:
        step_data = step['step']
        action = step_data.get('action', '')
        selector = step_data.get('selector', '')
        value = step_data.get('value', '')
        status = step['status']
        duration = step['duration'] if step['duration'] else ''
        error = step['error'] if step['error'] else ''
        
        html += f"""
            <tr class="step {status}">
                <td>{action}</td>
                <td>{selector}</td>
                <td>{value}</td>
                <td>{status}</td>
                <td>{duration}</td>
                <td>{error}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <h2>Failures</h2>
        <table>
            <tr>
                <th>Action</th>
                <th>Selector</th>
                <th>Value</th>
                <th>Error</th>
            </tr>
    """
    
    for failure in reporter.failures:
        step_data = failure['step']
        action = step_data.get('action', '')
        selector = step_data.get('selector', '')
        value = step_data.get('value', '')
        error = failure['error'] if failure['error'] else ''
        
        html += f"""
            <tr>
                <td>{action}</td>
                <td>{selector}</td>
                <td>{value}</td>
                <td>{error}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <h2>Warnings</h2>
        <table>
            <tr>
                <th>Action</th>
                <th>Selector</th>
                <th>Value</th>
                <th>Error</th>
            </tr>
    """
    
    for warning in reporter.warnings:
        step_data = warning['step']
        action = step_data.get('action', '')
        selector = step_data.get('selector', '')
        value = step_data.get('value', '')
        error = warning['error'] if warning['error'] else ''
        
        html += f"""
            <tr>
                <td>{action}</td>
                <td>{selector}</td>
                <td>{value}</td>
                <td>{error}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <h2>Network Requests</h2>
        <table>
            <tr>
                <th>URL</th>
                <th>Method</th>
                <th>Headers</th>
            </tr>
    """
    
    for request in reporter.network_requests:
        url = request['url']
        method = request['method']
        headers = json.dumps(request['headers'])
        
        html += f"""
            <tr>
                <td>{url}</td>
                <td>{method}</td>
                <td>{headers}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <h2>Network Responses</h2>
        <table>
            <tr>
                <th>URL</th>
                <th>Status</th>
                <th>Headers</th>
            </tr>
    """
    
    for response in reporter.network_responses:
        url = response['url']
        status = response['status']
        headers = json.dumps(response['headers'])
        
        html += f"""
            <tr>
                <td>{url}</td>
                <td>{status}</td>
                <td>{headers}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <h2>Console Messages</h2>
        <table>
            <tr>
                <th>Type</th>
                <th>Text</th>
            </tr>
    """
    
    for message in reporter.console_messages:
        message_type = message['type']
        text = message['text']
        
        html += f"""
            <tr>
                <td>{message_type}</td>
                <td>{text}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <h2>Screenshots</h2>
        <table>
            <tr>
                <th>Path</th>
                <th>Timestamp</th>
            </tr>
    """
    
    for screenshot in reporter.screenshots:
        path = screenshot['path']
        timestamp = datetime.fromtimestamp(screenshot['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        
        html += f"""
            <tr>
                <td>{path}</td>
                <td>{timestamp}</td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    with open(report_path, 'w') as f:
        f.write(html)

def _generate_csv_report(reporter, report_path):
    """
    Generate a CSV report.
    
    Args:
        reporter (TestReporter): The test reporter
        report_path (str): Path to save the report
    """
    # Create a DataFrame for steps
    steps_data = []
    for step in reporter.steps:
        step_data = step['step']
        steps_data.append({
            'action': step_data.get('action', ''),
            'selector': step_data.get('selector', ''),
            'value': step_data.get('value', ''),
            'status': step['status'],
            'duration': step['duration'] if step['duration'] else '',
            'error': step['error'] if step['error'] else '',
            'timestamp': datetime.fromtimestamp(step['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(steps_data)
    df.to_csv(report_path, index=False)

def _generate_excel_report(reporter, report_path):
    """
    Generate an Excel report.
    
    Args:
        reporter (TestReporter): The test reporter
        report_path (str): Path to save the report
    """
    # Create a writer object
    writer = pd.ExcelWriter(report_path, engine='openpyxl')
    
    # Create a DataFrame for steps
    steps_data = []
    for step in reporter.steps:
        step_data = step['step']
        steps_data.append({
            'action': step_data.get('action', ''),
            'selector': step_data.get('selector', ''),
            'value': step_data.get('value', ''),
            'status': step['status'],
            'duration': step['duration'] if step['duration'] else '',
            'error': step['error'] if step['error'] else '',
            'timestamp': datetime.fromtimestamp(step['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Create DataFrame and save to Excel
    df_steps = pd.DataFrame(steps_data)
    df_steps.to_excel(writer, sheet_name='Steps', index=False)
    
    # Create a DataFrame for failures
    failures_data = []
    for failure in reporter.failures:
        step_data = failure['step']
        failures_data.append({
            'action': step_data.get('action', ''),
            'selector': step_data.get('selector', ''),
            'value': step_data.get('value', ''),
            'error': failure['error'] if failure['error'] else '',
            'timestamp': datetime.fromtimestamp(failure['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Create DataFrame and save to Excel
    df_failures = pd.DataFrame(failures_data)
    df_failures.to_excel(writer, sheet_name='Failures', index=False)
    
    # Create a DataFrame for warnings
    warnings_data = []
    for warning in reporter.warnings:
        step_data = warning['step']
        warnings_data.append({
            'action': step_data.get('action', ''),
            'selector': step_data.get('selector', ''),
            'value': step_data.get('value', ''),
            'error': warning['error'] if warning['error'] else '',
            'timestamp': datetime.fromtimestamp(warning['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Create DataFrame and save to Excel
    df_warnings = pd.DataFrame(warnings_data)
    df_warnings.to_excel(writer, sheet_name='Warnings', index=False)
    
    # Create a DataFrame for network requests
    requests_data = []
    for request in reporter.network_requests:
        requests_data.append({
            'url': request['url'],
            'method': request['method'],
            'headers': json.dumps(request['headers']),
            'timestamp': datetime.fromtimestamp(request['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Create DataFrame and save to Excel
    df_requests = pd.DataFrame(requests_data)
    df_requests.to_excel(writer, sheet_name='Network Requests', index=False)
    
    # Create a DataFrame for network responses
    responses_data = []
    for response in reporter.network_responses:
        responses_data.append({
            'url': response['url'],
            'status': response['status'],
            'headers': json.dumps(response['headers']),
            'timestamp': datetime.fromtimestamp(response['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Create DataFrame and save to Excel
    df_responses = pd.DataFrame(responses_data)
    df_responses.to_excel(writer, sheet_name='Network Responses', index=False)
    
    # Create a DataFrame for console messages
    messages_data = []
    for message in reporter.console_messages:
        messages_data.append({
            'type': message['type'],
            'text': message['text'],
            'timestamp': datetime.fromtimestamp(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Create DataFrame and save to Excel
    df_messages = pd.DataFrame(messages_data)
    df_messages.to_excel(writer, sheet_name='Console Messages', index=False)
    
    # Create a DataFrame for screenshots
    screenshots_data = []
    for screenshot in reporter.screenshots:
        screenshots_data.append({
            'path': screenshot['path'],
            'timestamp': datetime.fromtimestamp(screenshot['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Create DataFrame and save to Excel
    df_screenshots = pd.DataFrame(screenshots_data)
    df_screenshots.to_excel(writer, sheet_name='Screenshots', index=False)
    
    # Create a DataFrame for summary
    summary = reporter.get_summary()
    summary_data = [
        {'Metric': 'Start Time', 'Value': datetime.fromtimestamp(summary['start_time']).strftime('%Y-%m-%d %H:%M:%S')},
        {'Metric': 'End Time', 'Value': datetime.fromtimestamp(summary['end_time']).strftime('%Y-%m-%d %H:%M:%S')},
        {'Metric': 'Duration (seconds)', 'Value': f"{summary['duration']:.2f}"},
        {'Metric': 'Total Steps', 'Value': summary['total_steps']},
        {'Metric': 'Successful Steps', 'Value': summary['successful_steps']},
        {'Metric': 'Failed Steps', 'Value': summary['failed_steps']},
        {'Metric': 'Warning Steps', 'Value': summary['warning_steps']},
        {'Metric': 'Network Requests', 'Value': summary['network_requests']},
        {'Metric': 'Network Responses', 'Value': summary['network_responses']},
        {'Metric': 'Console Messages', 'Value': summary['console_messages']},
        {'Metric': 'Screenshots', 'Value': summary['screenshots']}
    ]
    
    # Create DataFrame and save to Excel
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name='Summary', index=False)
    
    # Save the Excel file
    writer.close() 