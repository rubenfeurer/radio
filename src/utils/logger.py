import logging
import logging.handlers
from pathlib import Path

def setup_logger():
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logger
    logger = logging.getLogger("radio")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Prevent propagation to root logger
    
    # Create rotating file handler (10 MB per file, keep 5 backup files)
    file_handler = logging.handlers.RotatingFileHandler(
        filename="logs/radio.log",
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    # Set handler levels
    file_handler.setLevel(logging.DEBUG)
    console_handler.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers if they don't exist
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

# Create logger instance
logger = setup_logger()
