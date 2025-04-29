import os
import secrets

class Config:
    """
    Base configuration class.
    """
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DEBUG = False
    TESTING = False
    
    # Application paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
    SCREENSHOTS_FOLDER = os.path.join(BASE_DIR, 'screenshots')
    VPN_CONFIG_FOLDER = os.path.join(BASE_DIR, 'vpn_config')
    
    # Test execution settings
    DEFAULT_BROWSER = 'chromium'
    DEFAULT_HEADLESS = True
    DEFAULT_TIMEOUT = 30000  # milliseconds
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_DELAY = 1000  # milliseconds
    
    # Create necessary directories
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(REPORTS_FOLDER, exist_ok=True)
    os.makedirs(SCREENSHOTS_FOLDER, exist_ok=True)
    os.makedirs(VPN_CONFIG_FOLDER, exist_ok=True)

class DevelopmentConfig(Config):
    """
    Development configuration.
    """
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """
    Testing configuration.
    """
    DEBUG = True
    TESTING = True

class ProductionConfig(Config):
    """
    Production configuration.
    """
    DEBUG = False
    TESTING = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """
    Get the configuration based on the environment.
    
    Returns:
        Config: The configuration object
    """
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default']) 