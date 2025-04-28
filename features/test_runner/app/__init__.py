from flask import Flask
import os

def create_app():
    app = Flask(__name__)

    # Configure the app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing-only')

    # Import routes after app is created to avoid circular imports
    from .routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app
