from flask import Flask

# Create the Flask application
app = Flask(__name__, 
    template_folder='../../templates',  
    static_folder='../../static'        
)

# Import routes here to avoid circular imports
from src.app.routes import *

def create_app(test_config=None):
    if test_config is not None:
        app.config.update(test_config)
    return app