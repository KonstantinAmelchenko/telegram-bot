import os
from dotenv import load_dotenv

# Пытаемся загрузить .env (работает только локально на Mac)
load_dotenv()

# Настройки бота - читаем из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///events.db")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Проверка обязательных настроек
if not BOT_TOKEN:
    raise ValueError("❌ Не указан BOT_TOKEN в переменных окружения!")