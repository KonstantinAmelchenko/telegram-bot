import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///events.db")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Проверка обязательных настроек
if not BOT_TOKEN:
    raise ValueError("❌ Не указан BOT_TOKEN в файле .env!")