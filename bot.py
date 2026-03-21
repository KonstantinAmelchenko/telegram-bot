import asyncio
import logging
from aiogram import Bot
from config import BOT_TOKEN
from database import init_db
from handlers import dp

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)

async def main():
    await init_db()
    logging.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())