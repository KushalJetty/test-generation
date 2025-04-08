import os
import uuid
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environment

def generate_chart(data, chart_type='pie', filename=None):
    """Generate a chart based on test results data.
    
    Args:
        data: Dictionary with test result counts
        chart_type: Type of chart to generate ('pie', 'bar', etc.)
        filename: Optional filename to save the chart
        
    Returns:
        Path to the saved chart image
    """
    plt.figure(figsize=(8, 6))
    
    if chart_type == 'pie':
        # Create a pie chart
        labels = list(data.keys())
        sizes = list(data.values())
        colors = ['#28a745', '#dc3545', '#ffc107', '#6c757d']
        explode = (0.1, 0, 0, 0)  # explode the 1st slice (passed)
        
        plt.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=140)
        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        plt.title('Test Results Distribution')
        
    elif chart_type == 'bar':
        # Create a bar chart
        categories = list(data.keys())
        values = list(data.values())
        colors = ['#28a745', '#dc3545', '#ffc107', '#6c757d']
        
        plt.bar(categories, values, color=colors)
        plt.xlabel('Status')
        plt.ylabel('Count')
        plt.title('Test Results by Status')
    
    # Save the chart
    if not filename:
        filename = f"chart_{uuid.uuid4().hex[:8]}.png"
    
    from flask import current_app
    chart_dir = os.path.join(current_app.static_folder, 'charts')
    os.makedirs(chart_dir, exist_ok=True)
    chart_path = os.path.join(chart_dir, filename)
    
    plt.savefig(chart_path)
    plt.close()
    
    return os.path.join('static', 'charts', filename)