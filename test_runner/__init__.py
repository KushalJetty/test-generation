from flask import Blueprint

# Create a Blueprint for the test runner
test_runner_bp = Blueprint('test_runner', __name__, url_prefix='/test-runner')

# Import routes after creating the Blueprint to avoid circular imports
from . import routes 