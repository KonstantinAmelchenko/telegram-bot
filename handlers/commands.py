from aiogram import Bot
from aiogram.types import BotCommand

async def set_commands(bot: Bot):
    """Регистрирует команды бота в Telegram"""
    commands = [
        BotCommand(command="start", description="👋 Запустить бота"),
        BotCommand(command="events", description="📋 Показать мероприятия"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="create_event", description="(admin)"),
        BotCommand(command="list_events", description="(admin)"),
        BotCommand(command="delete_event", description="(admin)")
    ]
    
    await bot.set_my_commands(commands)