
import json
import os
import pandas as pd
import time
from datetime import datetime

class TestReporter:
    """
    Collects and manages test execution data for reporting.
    """
    
    def __init__(self):
        """Initialize the test reporter with empty metrics"""
        self.start_time = time.time()
        self.metrics = {
            'summary': {
                'start_time': datetime.now().isoformat(),
                'end_time': None,
                'duration': 0,
                'total_steps': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'retried': 0
            },
            'steps': [],
            'network': [],
            'console': []
        }
        
    def record_step(self, result, execution_time=0):
        """
        Record the result of a test step.
        
        Args:
            result (dict): The result of the step execution
            execution_time (float): Time taken to execute the step
        """
        step_data = {
            'step_number': len(self.metrics['steps']) + 1,
            'action': result['step'].get('action'),
            'selector': result['step'].get('selector', ''),
            'value': result['step'].get('value', ''),
            'status': result.get('status', 'unknown'),
            'message': result.get('message', ''),
            'retries': result.get('retries', 0),
            'execution_time': execution_time
        }
        
        self.metrics['steps'].append(step_data)
        
        # Update summary metrics
        self.metrics['summary']['total_steps'] += 1
        
        if step_data['status'] == 'passed':
            self.metrics['summary']['passed'] += 1
        elif step_data['status'] == 'failed':
            self.metrics['summary']['failed'] += 1
        elif step_data['status'] == 'skipped':
            self.metrics['summary']['skipped'] += 1
            
        if step_data['retries'] > 0:
            self.metrics['summary']['retried'] += 1
            
    def record_network_request(self, request):
        """
        Record a network request.
        
        Args:
            request: Playwright request object
        """
        request_data = {
            'url': request.url,
            'method': request.method,
            'headers': request.headers,
            'timestamp': datetime.now().isoformat(),
            'resource_type': request.resource_type
        }
        
        self.metrics['network'].append(request_data)
        
    def record_network_response(self, response):
        """
        Record a network response.
        
        Args:
            response: Playwright response object
        """
        # Find the matching request
        for request in self.metrics['network']:
            if request['url'] == response.url:
                request['status'] = response.status
                request['status_text'] = response.status_text
                break
                
    def record_console_message(self, message):
        """
        Record a console message.
        
        Args:
            message: Console message object
        """
        message_data = {
            'type': message.type,
            'text': message.text,
            'timestamp': datetime.now().isoformat()
        }
        
        self.metrics['console'].append(message_data)
        
    def get_results(self):
        """
        Get the complete test results.
        
        Returns:
            dict: The test metrics and results
        """
        # Update final metrics
        self.metrics['summary']['end_time'] = datetime.now().isoformat()
        self.metrics['summary']['duration'] = time.time() - self.start_time
        
        return self.metrics
        
def generate_report(results, format='json', output_dir='reports'):
    """
    Generate a test report in the specified format.
    
    Args:
        results (dict): Test results from TestReporter
        format (str): Output format ('json', 'csv', 'html', 'xlsx')
        output_dir (str): Directory to save the report
        
    Returns:
        str: Path to the generated report file
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate a timestamp for the filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format == 'json':
        # JSON format
        filename = f"{output_dir}/report_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
            
    elif format == 'csv':
        # CSV format - separate files for different sections
        base_filename = f"{output_dir}/report_{timestamp}"
        
        # Summary CSV
        summary_df = pd.DataFrame([results['summary']])
        summary_df.to_csv(f"{base_filename}_summary.csv", index=False)
        
        # Steps CSV
        if results['steps']:
            steps_df = pd.DataFrame(results['steps'])
            steps_df.to_csv(f"{base_filename}_steps.csv", index=False)
            
        # Network CSV
        if results['network']:
            network_df = pd.DataFrame(results['network'])
            network_df.to_csv(f"{base_filename}_network.csv", index=False)
            
        # Console CSV
        if results['console']:
            console_df = pd.DataFrame(results['console'])
            console_df.to_csv(f"{base_filename}_console.csv", index=False)
            
        filename = f"{base_filename}.csv"
        
    elif format == 'xlsx':
        # Excel format - all sections in different sheets
        filename = f"{output_dir}/report_{timestamp}.xlsx"
        
        with pd.ExcelWriter(filename) as writer:
            # Summary sheet
            summary_df = pd.DataFrame([results['summary']])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Steps sheet
            if results['steps']:
                steps_df = pd.DataFrame(results['steps'])
                steps_df.to_excel(writer, sheet_name='Steps', index=False)
                
            # Network sheet
            if results['network']:
                network_df = pd.DataFrame(results['network'])
                network_df.to_excel(writer, sheet_name='Network', index=False)
                
            # Console sheet
            if results['console']:
                console_df = pd.DataFrame(results['console'])
                console_df.to_excel(writer, sheet_name='Console', index=False)
                
    elif format == 'html':
        # HTML format
        filename = f"{output_dir}/report_{timestamp}.html"
        
        # Create a simple HTML report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Execution Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .passed {{ color: green; }}
                .failed {{ color: red; }}
                .skipped {{ color: orange; }}
            </style>
        </head>
        <body>
            <h1>Test Execution Report</h1>
            <h2>Summary</h2>
            <table>
                <tr>
                    <th>Start Time</th>
                    <td>{results['summary']['start_time']}</td>
                </tr>
                <tr>
                    <th>End Time</th>
                    <td>{results['summary']['end_time']}</td>
                </tr>
                <tr>
                    <th>Duration</th>
                    <td>{results['summary']['duration']:.2f} seconds</td>
                </tr>
                <tr>
                    <th>Total Steps</th>
                    <td>{results['summary']['total_steps']}</td>
                </tr>
                <tr>
                    <th>Passed</th>
                    <td class="passed">{results['summary']['passed']}</td>
                </tr>
                <tr>
                    <th>Failed</th>
                    <td class="failed">{results['summary']['failed']}</td>
                </tr>
                <tr>
                    <th>Skipped</th>
                    <td class="skipped">{results['summary']['skipped']}</td>
                </tr>
                <tr>
                    <th>Retried</th>
                    <td>{results['summary']['retried']}</td>
                </tr>
            </table>
        """
        
        # Add steps table
        if results['steps']:
            html_content += """
            <h2>Steps</h2>
            <table>
                <tr>
                    <th>#</th>
                    <th>Action</th>
                    <th>Selector</th>
                    <th>Value</th>
                    <th>Status</th>
                    <th>Retries</th>
                    <th>Time (s)</th>
                    <th>Message</th>
                </tr>
            """
            
            for step in results['steps']:
                status_class = step['status']
                html_content += f"""
                <tr>
                    <td>{step['step_number']}</td>
                    <td>{step['action']}</td>
                    <td>{step['selector']}</td>
                    <td>{step['value']}</td>
                    <td class="{status_class}">{step['status']}</td>
                    <td>{step['retries']}</td>
                    <td>{step['execution_time']:.2f}</td>
                    <td>{step['message']}</td>
                </tr>
                """
                
            html_content += "</table>"
            
        # Add network requests table
        if results['network']:
            html_content += """
            <h2>Network Requests</h2>
            <table>
                <tr>
                    <th>URL</th>
                    <th>Method</th>
                    <th>Status</th>
                    <th>Type</th>
                    <th>Timestamp</th>
                </tr>
            """
            
            for req in results['network']:
                html_content += f"""
                <tr>
                    <td>{req['url']}</td>
                    <td>{req['method']}</td>
                    <td>{req.get('status', '-')}</td>
                    <td>{req['resource_type']}</td>
                    <td>{req['timestamp']}</td>
                </tr>
                """
                
            html_content += "</table>"
            
        # Add console messages table
        if results['console']:
            html_content += """
            <h2>Console Messages</h2>
            <table>
                <tr>
                    <th>Type</th>
                    <th>Message</th>
                    <th>Timestamp</th>
                </tr>
            """
            
            for msg in results['console']:
                html_content += f"""
                <tr>
                    <td>{msg['type']}</td>
                    <td>{msg['text']}</td>
                    <td>{msg['timestamp']}</td>
                </tr>
                """
                
            html_content += "</table>"
            
        html_content += """
        </body>
        </html>
        """
        
        with open(filename, 'w') as f:
            f.write(html_content)
    else:
        # Default to JSON if format is not recognized
        filename = f"{output_dir}/report_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
            
    return filename

