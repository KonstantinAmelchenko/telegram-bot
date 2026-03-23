import asyncio
import logging
from aiogram import Bot
from config import BOT_TOKEN
from database import init_db
from handlers import dp
from handlers.commands import set_commands

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)

async def main():
    await init_db()
    await set_commands(bot)
    logging.info("Бот запускается...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()  # ✅ Закрываем сессию
        logging.info("Бот остановлен")

if __name__ == "__main__":  # ✅ Исправлено: было "if name == "main""
    asyncio.run(main())