import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-cognitest'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///cognitest.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # AI Model paths
    TEST_GENERATION_MODEL_PATH = os.environ.get('TEST_GEN_MODEL') or 'models/test_gen_model.h5'
    VISUAL_REGRESSION_MODEL_PATH = os.environ.get('VIS_REG_MODEL') or 'models/visual_reg_model.h5'
    
    # Device farm configuration
    DEVICE_FARM_URL = os.environ.get('DEVICE_FARM_URL') or 'http://localhost:4723/wd/hub'
    
    # Browser configurations
    SUPPORTED_BROWSERS = ['chrome', 'firefox', 'safari', 'edge']
    
    # Mobile device configurations
    SUPPORTED_MOBILE_PLATFORMS = ['android', 'ios']