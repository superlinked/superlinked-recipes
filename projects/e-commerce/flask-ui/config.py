# config.py
import os
from datetime import timedelta

class BaseConfig:
    """Base configuration."""
    # Flask settings
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Data settings
    PRODUCTS_GCS_PATH = os.environ.get('GCS_PRODUCTS_PATH')
    
    # API endpoints configuration
    API_HOST = os.environ.get('API_HOST', 'http://0.0.0.0')
    API_PORT = os.environ.get('API_PORT', '8000')
    API_BASE_URL = f"{API_HOST}:{API_PORT}"

class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    # You can override any BaseConfig settings here
    API_HOST = 'http://0.0.0.0'
    API_PORT = '8000'

class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    # Override with production settings
    API_HOST = os.environ.get('API_HOST', 'https://api.production.com')
    API_PORT = os.environ.get('API_PORT', '443')

# Dictionary to map environment names to config classes
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}