import asyncio
import logging
import os
import threading
import time
from aiogram import Bot
from config import BOT_TOKEN
from database import init_db
from handlers import dp
from handlers.commands import set_commands

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)


def maybe_start_embedded_vk_bot() -> None:
    if os.getenv("EMBEDDED_VK_BOT", "1") != "1":
        logging.info("Embedded VK bot is disabled by EMBEDDED_VK_BOT")
        return

    has_vk_env = all([
        os.getenv("VK_GROUP_TOKEN"),
        os.getenv("VK_GROUP_ID"),
        os.getenv("TELEGRAM_BOT_USERNAME"),
    ])
    if not has_vk_env:
        logging.info("VK bot not started: VK env vars are missing")
        return

    def run_vk() -> None:
        while True:
            try:
                from vk_bot import main as vk_main
                vk_main()
            except Exception:
                logging.exception("Embedded VK bot crashed, restart in 5s")
                time.sleep(5)

    thread = threading.Thread(target=run_vk, name="vk-bot-thread", daemon=True)
    thread.start()
    logging.info("Embedded VK bot thread started")


async def main():
    await init_db()
    maybe_start_embedded_vk_bot()
    await set_commands(bot)
    logging.info("Бот запускается...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()  # ✅ Закрываем сессию
        logging.info("Бот остановлен")

if __name__ == "__main__":  # ✅ Исправлено: было "if name == "main""
    asyncio.run(main())
