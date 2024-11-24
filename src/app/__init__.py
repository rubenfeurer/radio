from flask import Flask

def create_app(test_config=None):
    app = Flask(__name__, 
                template_folder='../../templates',
                static_folder='../../static')
    
    if test_config is not None:
        app.config.update(test_config)
    
    # Import routes after app is created to avoid circular imports
    from src.app.routes import register_routes
    register_routes(app)
    
    return app

# Create a default app instance for non-testing scenarios
app = create_app() 