import tomli
import os
import logging

logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from TOML file"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'config.toml')
        with open(config_path, 'rb') as f:
            config = tomli.load(f)
            logger.info("Configuration loaded successfully")
            return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise 