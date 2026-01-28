import os
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
if not ADMIN_ID:
    raise ValueError("ADMIN_ID не найден в .env файле")

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
if not CHANNEL_USERNAME:
    raise ValueError("CHANNEL_USERNAME не найден в .env файле")

# Лимиты
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "10"))
MAX_PHOTO_SIZE_MB = int(os.getenv("MAX_PHOTO_SIZE_MB", "15"))
MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "100"))

# Конвертация в байты
MAX_PHOTO_SIZE_BYTES = MAX_PHOTO_SIZE_MB * 1024 * 1024
MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024

# База данных
DB_PATH = "bot.db"

# Логирование
LOG_FILE = "bot.log"
LOG_LEVEL = "INFO"
