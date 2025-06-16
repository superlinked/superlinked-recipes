from flask import Flask
from flask_session import Session
from config import config
import os
from dotenv import main as main_dotenv

def create_app(config_name=None):
    # from dotenv import main
    main_dotenv.load_dotenv()
    app = Flask(__name__)
    
    # Set configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app.config.from_object(config[config_name])
    
    Session(app)
    
    from app.routes import main
    app.register_blueprint(main)
    
    return app