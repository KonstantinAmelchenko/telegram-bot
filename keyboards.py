from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

EVENTS = {
    1: "🎨 Рисование",
    2: "🏃 Забег",
    3: "📚 Книги",
    4: "🎮 Игры"
}

def get_events_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for event_id, event_name in EVENTS.items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=event_name, callback_data=f"event_{event_id}")
        ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="👤 Профиль", callback_data="profile")])
    return keyboard

def get_confirm_keyboard(event_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
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