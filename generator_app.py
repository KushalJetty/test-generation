from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from models import db, Project, TestSuite, TestCase
from streamzai_test_generator import StreamzAITestGenerator
import os
import re

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'generator-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///streamzai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

@app.route('/')
def index():
    """Show the main generator interface."""
    return render_template('generator_index.html')

@app.route('/generate/<int:suite_id>')
def generate_test_cases(suite_id):
    """Generate test cases for a test suite."""
    test_suite = TestSuite.query.get_or_404(suite_id)
    project = test_suite.project
    
    # Create a generator instance
    generator = StreamzAITestGenerator()
    
    # Find all supported files
    supported_files = generator.traverse_directory(project.path)
    
    # Generate test cases for each file
    for file_path in supported_files:
        # Analyze file
        file_analysis = generator.analyze_file(file_path)
        
        # Generate test case
        test_case_result = generator.generate_test_case(file_analysis)
        
        if "error" not in test_case_result:
            # Create test case in database
            rel_path = os.path.relpath(file_path, start=project.path)
            file_name = os.path.basename(file_path)
            file_base, file_ext = os.path.splitext(file_name)
            
            # Create appropriate test file name based on language
            language = file_analysis["language"]
            if language == "python":
                test_file_name = f"test_{file_base}{file_ext}"
            else:
                test_file_name = f"{file_base}.test{file_ext}"
            
            # Create directory structure in output directory
            rel_dir = os.path.dirname(rel_path)
            test_dir = os.path.join("generated_tests", project.name, rel_dir)
            os.makedirs(test_dir, exist_ok=True)
            
            # Save test content to file
            test_file_path = os.path.join(test_dir, test_file_name)
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_case_result["test_content"])
            
            # Create test case in database
            test_case = TestCase(
                original_file_path=file_path,
                test_file_path=test_file_path,
                language=language,
                test_suite_id=test_suite.id
            )
            db.session.add(test_case)
    
    db.session.commit()
    flash('Test cases generated successfully!', 'success')
    return render_template('generator_success.html', test_suite=test_suite)

if __name__ == '__main__':
    app.run(debug=True, port=5000) 