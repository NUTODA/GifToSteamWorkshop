import os

from dotenv import load_dotenv

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
FSM_STORAGE = os.getenv('FSM_STORAGE', 'memory').strip().lower()
REDIS_URL = os.getenv('REDIS_URL', '').strip()
_SUPPORTED_LOCALES = {'ru', 'en', 'uk'}
_default_locale_raw = os.getenv('DEFAULT_LOCALE', 'ru').strip().lower()
DEFAULT_LOCALE = _default_locale_raw if _default_locale_raw in _SUPPORTED_LOCALES else 'ru'

SHUTDOWN_TASK_WAIT_TIMEOUT = int(os.getenv('SHUTDOWN_TASK_WAIT_TIMEOUT', '30'))
FFMPEG_TERMINATE_TIMEOUT = int(os.getenv('FFMPEG_TERMINATE_TIMEOUT', '5'))

HEARTBEAT_FILE = os.getenv('HEARTBEAT_FILE', '/tmp/steam_showcase_bot.heartbeat')
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv('HEARTBEAT_INTERVAL_SECONDS', '5'))
HEALTHCHECK_MAX_STALENESS_SECONDS = int(os.getenv('HEALTHCHECK_MAX_STALENESS_SECONDS', '20'))

DEBUG_MODE = (LOG_LEVEL or '').upper() == 'DEBUG' or os.getenv('BOT_DEBUG', '') == '1'
