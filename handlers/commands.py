from aiogram import Bot
from aiogram.types import BotCommand

async def set_commands(bot: Bot):
    """Регистрирует команды бота в Telegram"""
    commands = [
        BotCommand(command="start", description="👋 Запустить бота"),
        BotCommand(command="events", description="📋 Показать мероприятия"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="create_event", description="➕ Создать мероприятие (админ)"),
        BotCommand(command="list_events", description="📝 Список мероприятий (админ)"),
        BotCommand(command="delete_event", description="❌ Удалить мероприятие (админ)")
    ]
    
    await bot.set_my_commands(commands)