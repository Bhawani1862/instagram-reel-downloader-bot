import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID', None)

# Download Settings
MAX_DOWNLOAD_SIZE = int(os.getenv('MAX_DOWNLOAD_SIZE', 500))  # MB
MAX_BATCH_DOWNLOADS = int(os.getenv('MAX_BATCH_DOWNLOADS', 5))
DOWNLOAD_TIMEOUT = int(os.getenv('DOWNLOAD_TIMEOUT', 60))  # seconds

# File Paths
DOWNLOAD_DIR = 'downloads'
LOG_DIR = 'logs'
DB_PATH = 'bot_database.db'

# Create directories if they don't exist
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Instagram Quality Settings
QUALITY_OPTIONS = {
    'best': 'Best Quality (HD)',
    'good': 'Good Quality (720p)',
    'low': 'Low Quality (480p)'
}

DEFAULT_QUALITY = 'best'