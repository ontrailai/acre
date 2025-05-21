import logging
import os
import sys
from datetime import datetime

# Create logs directory if it doesn't exist
logs_dir = os.path.join("app", "logs")
os.makedirs(logs_dir, exist_ok=True)

# Configure logger
logger = logging.getLogger("lease_logik")
logger.setLevel(logging.INFO)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Create file handler
log_file = os.path.join(logs_dir, f"lease_logik_{datetime.now().strftime('%Y%m%d')}.log")
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger.info(f"Calling function: {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"Function {func.__name__} completed")
        return result
    return wrapper
