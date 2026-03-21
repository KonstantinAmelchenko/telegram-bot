from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

EVENTS = {
    1: "🎨 Рисование",
    2: "🏃 Забег",
    3: "📚 Книги",
    4: "🎮 Игры"
}

def get_events_keyboard(user_registrations: list = None):
    if user_registrations is None:
        user_registrations = []
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for event_id, event_name in EVENTS.items():
        status = " ✅" if event_id in user_registrations else ""
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"{event_name}{status}", callback_data=f"event_{event_id}")
        ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="👤 Профиль", callback_data="profile")])
    return keyboard

def get_register_keyboard(event_id: int):
    """Клавиатура для записи (если не записан)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Записаться", callback_data=f"register_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_registered_keyboard(event_id: int):
    """Клавиатура для уже записанных"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"unregister_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_profile_keyboard():
    """Без кнопки Назад"""
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