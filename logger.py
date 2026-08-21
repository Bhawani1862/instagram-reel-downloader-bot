import logging
import os
from datetime import datetime
from config import LOG_DIR

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
log_file = os.path.join(LOG_DIR, f'bot_{datetime.now().strftime("%Y%m%d")}.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def log_download(user_id, url, status, filename=None):
    """Log download activity"""
    logger.info(f"User {user_id} - URL: {url} - Status: {status} - File: {filename}")

def log_error(user_id, error_msg):
    """Log errors"""
    logger.error(f"User {user_id} - Error: {error_msg}")