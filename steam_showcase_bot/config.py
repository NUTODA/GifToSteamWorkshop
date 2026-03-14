from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

LOG_FILE = os.getenv('LOG_FILE', 'steam_showcase_bot.log')
LOG_TO_FILE = os.getenv('LOG_TO_FILE', '1') in ('1', 'true', 'True')

SAVE_UPLOADS = os.getenv('SAVE_UPLOADS', '1') in ('1', 'true', 'True')

TELEGRAM_CLIENT_TIMEOUT = int(os.getenv('TELEGRAM_CLIENT_TIMEOUT', '300'))
TELEGRAM_CLIENT_CONNECT_LIMIT = int(os.getenv('TELEGRAM_CLIENT_CONNECT_LIMIT', '0'))

MAX_ARCHIVE_SEND_MB = int(os.getenv('MAX_ARCHIVE_SEND_MB', '50'))
ZIP_SEND_RETRIES = int(os.getenv('ZIP_SEND_RETRIES', '3'))
ZIP_SEND_TIMEOUT = int(os.getenv('ZIP_SEND_TIMEOUT', '300'))

RATE_LIMIT_SECONDS = float(os.getenv('RATE_LIMIT_SECONDS', '30'))
MAX_CONCURRENT_TASKS = int(os.getenv('MAX_CONCURRENT_TASKS', '3'))
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '20'))

DEBUG_MODE = (LOG_LEVEL or '').upper() == 'DEBUG' or os.getenv('BOT_DEBUG', '') == '1'
