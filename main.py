import os
import sys
from src.app.routes import app
from src.hardware.gpio_handler import GPIOHandler
import atexit

# Initialize GPIO handler
gpio_handler = GPIOHandler()

# Register cleanup
atexit.register(gpio_handler.cleanup)

def create_app(test_config=None):
    if test_config is not None:
        app.config.update(test_config)
    return app

if __name__ == '__main__':
    try:
        # Add project root to Python path
        project_root = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(project_root)
        
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        print(f"Error running app: {e}") 