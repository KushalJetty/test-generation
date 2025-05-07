import os
import sys
import subprocess
import json
import tempfile
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_uploads')
ALLOWED_EXTENSIONS = {'py'}
INPUT_VALUES_PATH = os.path.join('tests', 'input_values.json')

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_input_values():
    """Load input values from the JSON file."""
    try:
        if os.path.exists(INPUT_VALUES_PATH):
            with open(INPUT_VALUES_PATH, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading input values: {e}")
        return {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        return jsonify({
            'success': True,
            'filename': filename,
            'path': file_path
        })

    return jsonify({'error': 'File type not allowed'}), 400

@app.route('/upload_input_file', methods=['POST'])
def upload_input_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Allow only JSON files for input values
    if file and file.filename.endswith('.json'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Validate that the file contains valid JSON
        try:
            with open(file_path, 'r') as f:
                json.load(f)
        except json.JSONDecodeError:
            os.remove(file_path)  # Remove invalid file
            return jsonify({'error': 'Invalid JSON file'}), 400

        return jsonify({
            'success': True,
            'filename': filename,
            'path': file_path
        })

    return jsonify({'error': 'File type not allowed. Only JSON files are accepted.'}), 400

@app.route('/run_test', methods=['POST'])
def run_test():
    data = request.get_json()
    file_path = data.get('file_path')

    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Invalid file path'}), 400

    try:
        # Run the test file using Python
        result = subprocess.run(
            [sys.executable, file_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        return jsonify({
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Test execution timed out after 5 minutes'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get_input_sets', methods=['GET'])
def get_input_sets():
    """Get available input sets from the JSON file."""
    try:
        input_data = load_input_values()

        # Check if the input data has the expected structure
        if 'test_sets' in input_data:
            return jsonify({'input_sets': input_data['test_sets']})

        # For the existing input_values.json format
        # Convert the flat key-value structure to a list of input sets
        input_sets = [{'name': 'Default Values', 'inputs': input_data}]
        return jsonify({'input_sets': input_sets})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/run_test_with_config', methods=['POST'])
def run_test_with_config():
    """Run a test with the specified configuration."""
    data = request.get_json()
    file_path = data.get('file_path')
    input_mode = data.get('input_mode', 'default')
    input_set = data.get('input_set')
    input_file_path = data.get('input_file_path')
    headless = data.get('headless', False)

    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Invalid test file path'}), 400

    try:
        # For default input mode, just run the test file directly
        if input_mode == 'default':
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            return jsonify({
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            })

        # For existing custom input mode, use the test runner script
        elif input_mode == 'existing' and input_set:
            # Check if a custom input file was uploaded
            if not input_file_path or not os.path.exists(input_file_path):
                return jsonify({'error': 'Invalid input file path'}), 400

            # Run the test using the test runner script
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_runner_script.py'),
                '--test', file_path,
                '--input', input_file_path,
                '--set', input_set
            ]

            if headless:
                cmd.append('--headless')

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            return jsonify({
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            })

        # For dynamic input mode, just run the test file directly for now
        # In a real implementation, this would handle dynamic input differently
        else:
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            return jsonify({
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            })

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Test execution timed out after 5 minutes'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/temp_uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
