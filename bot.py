import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import dp  # Импортируем dp из handlers.py

# ==================== НАСТРОЙКИ ====================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)

# ==================== ЗАПУСК ====================
async def main():
    """Основная функция запуска"""
    await init_db()
    logging.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())