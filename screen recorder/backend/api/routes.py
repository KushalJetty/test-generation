from flask import Blueprint, jsonify, request
from ..services.recorder_service import RecorderService
from ..services.test_generator_service import TestGeneratorService

api_bp = Blueprint('api', __name__)
recorder_service = RecorderService()
test_generator_service = TestGeneratorService()

@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'CogniTest API',
        'version': '0.1.0'
    })

@api_bp.route('/generate-tests', methods=['POST'])
def generate_tests():
    data = request.json
    url = data.get('url')
    test_types = data.get('test_types', ['functional', 'ui'])
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        tests = test_generator_service.generate_from_url(url, test_types)
        return jsonify(tests)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/start-recording', methods=['POST'])
def start_recording():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        success = recorder_service.start_recording(url)
        return jsonify({'success': success, 'message': 'Recording started'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add more API routes here