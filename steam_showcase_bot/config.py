from dotenv import load_dotenv
import os

load_dotenv()  # загрузить переменные из .env (если файл в рабочей папке)

# Основные переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Logging configuration
LOG_FILE = os.getenv('LOG_FILE', 'steam_showcase_bot.log')
LOG_TO_FILE = os.getenv('LOG_TO_FILE', '1') in ('1', 'true', 'True')

# Feature flags
SAVE_UPLOADS = os.getenv('SAVE_UPLOADS', '1') in ('1', 'true', 'True')
