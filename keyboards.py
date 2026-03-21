from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_events_keyboard(user_registrations: list = None, event_counts: dict = None, events: list = None):
    """Клавиатура со списком мероприятий из БД"""
    if user_registrations is None:
        user_registrations = []
    if event_counts is None:
        event_counts = {}
    if events is None:
        events = []
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    # events приходит как список кортежей: (id, name, date, time)
    for event_id, event_name, event_date, event_time in events:
        status = " ✅" if event_id in user_registrations else ""
        count = event_counts.get(event_id, 0)
        # Формируем текст кнопки: Название | Дата Время ✅ 👥 N
        event_text = f"{event_name} | {event_date} {event_time}{status} 👥 {count}"
        
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=event_text, callback_data=f"event_{event_id}")
        ])
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="👤 Профиль", callback_data="profile")])
    return keyboard

def get_register_keyboard(event_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Записаться", callback_data=f"register_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_registered_keyboard(event_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"unregister_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_profile_keyboard():
    """Клавиатура профиля (исправлены пробелы)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить ник", callback_data="edit_nickname")],
        [InlineKeyboardButton(text="📷 Изменить фото", callback_data="edit_photo")],
        [InlineKeyboardButton(text="📋 Мероприятия", callback_data="show_events")]
    ])

def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Мероприятия")],
        [KeyboardButton(text="👤 Профиль")]
    ], resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)

def get_skip_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⏭️ Пропустить")]
    ], resize_keyboard=True)