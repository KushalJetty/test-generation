import os

class Config:
    """Base configuration class"""
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-for-testing-only')
    DEBUG = False
    TESTING = False
    
    # Application paths
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, '..', 'uploads')
    REPORT_FOLDER = os.path.join(BASE_DIR, '..', 'reports')
    SCREENSHOT_FOLDER = os.path.join(BASE_DIR, '..', 'screenshots')
    
    # Ensure directories exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(REPORT_FOLDER, exist_ok=True)
    os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)
    
    # Test execution settings
    DEFAULT_BROWSER = 'chromium'
    DEFAULT_HEADLESS = False
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_STOP_ON_FAILURE = False
    DEFAULT_REPORT_FORMAT = 'json'
    
    # VPN settings
    VPN_ENABLED = False
    VPN_CONFIG_FOLDER = os.path.join(BASE_DIR, '..', 'vpn_configs')
    os.makedirs(VPN_CONFIG_FOLDER, exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
class ProductionConfig(Config):
    """Production configuration"""
    # In production, set SECRET_KEY from environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Set secure defaults
    DEFAULT_HEADLESS = True

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get the current configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'default')
    return config.get(env, config['default'])
