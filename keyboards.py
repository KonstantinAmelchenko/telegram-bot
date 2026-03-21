from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

EVENTS = {
    1: "🎨 Мастер-класс по рисованию",
    2: "🏃 Забег в парке",
    3: "📚 Книжный клуб",
    4: "🎮 Игровой вечер"
}

def get_events_keyboard(user_registrations: list = None):
    """Клавиатура со списком мероприятий"""
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

def get_confirm_keyboard(event_id: int):
    """Клавиатура подтверждения записи"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_registered_keyboard(event_id: int):
    """Клавиатура для уже записанных"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Участники", callback_data=f"participants_{event_id}")],
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"unregister_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_participants_keyboard(event_id: int):
    """Клавиатура просмотра участников"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"unregister_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_profile_keyboard():
    """Клавиатура профиля"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить ник", callback_data="edit_nickname")],
        [InlineKeyboardButton(text="📷 Изменить фото", callback_data="edit_photo")],
        [InlineKeyboardButton(text="📋 Мероприятия", callback_data="show_events")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_main_menu_keyboard():
    """Основное меню с кнопками в чате"""
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Мероприятия")],
        [KeyboardButton(text="👤 Профиль")]
    ], resize_keyboard=True)

def get_cancel_keyboard():
    """Клавиатура отмены"""
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)

def get_skip_keyboard():
    """Клавиатура пропуска шага"""
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⏭️ Пропустить")]
    ], resize_keyboard=True)