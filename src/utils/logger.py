import logging
import logging.handlers
import os
from pathlib import Path

def setup_logger():
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logger
    logger = logging.getLogger("radio")
    logger.setLevel(logging.DEBUG)
    
    # Create rotating file handler (10 MB per file, keep 5 backup files)
    handler = logging.handlers.RotatingFileHandler(
        filename="logs/radio.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger

# Create logger instance
logger = setup_logger() 