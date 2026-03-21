from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==================== НАСТРОЙКИ МЕРОПРИЯТИЙ ====================
EVENTS = {
    1: "🎨 Мастер-класс по рисованию",
    2: "🏃 Забег в парке",
    3: "📚 Книжный клуб",
    4: "🎮 Игровой вечер"
}

# ==================== КЛАВИАТУРЫ ====================
def get_events_keyboard():
    """Клавиатура со списком мероприятий"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for event_id, event_name in EVENTS.items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=event_name, callback_data=f"event_{event_id}")
        ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel")])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")])
    return keyboard

def get_confirm_keyboard(event_id: int):
    """Клавиатура подтверждения записи"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_participants_keyboard(event_id: int):
    """Клавиатура просмотра участников"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Посмотреть участников", callback_data=f"participants_{event_id}")],
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
        [KeyboardButton(text="👤 Мой профиль")]
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