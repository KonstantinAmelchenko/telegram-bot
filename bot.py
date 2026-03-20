import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================== НАСТРОЙКИ ====================
TOKEN = "8601506854:AAEwGf70yUM0iVHSyYcmwg5X7oBcmWHeKeE"  # <-- Вставь сюда свой токен
DB_NAME = "events.db"

EVENTS = {
    1: "🎨 Мастер-класс по рисованию",
    2: "🏃 Забег в парке",
    3: "📚 Книжный клуб",
    4: "🎮 Игровой вечер"
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==================== МАШИНА СОСТОЯНИЙ (FSM) ====================
class ProfileSetup(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_photo = State()

# ==================== БАЗА ДАННЫХ ====================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                nickname TEXT,
                photo_id TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS registrations (
                user_id INTEGER PRIMARY KEY,
                event_id INTEGER
            )
        ''')
        await db.commit()

async def save_profile(user_id: int, username: str, nickname: str, photo_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            '''INSERT OR REPLACE INTO profiles (user_id, username, nickname, photo_id) 
               VALUES (?, ?, ?, ?)''',
            (user_id, username, nickname, photo_id)
        )
        await db.commit()

async def register_for_event(user_id: int, event_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                'INSERT INTO registrations (user_id, event_id) VALUES (?, ?)',
                (user_id, event_id)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def get_event_participants(event_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute('''
            SELECT p.nickname, p.photo_id 
            FROM registrations r
            JOIN profiles p ON r.user_id = p.user_id
            WHERE r.event_id = ?
        ''', (event_id,))
        return await cursor.fetchall()

async def check_user_registration(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'SELECT event_id FROM registrations WHERE user_id = ?',
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else None

async def unregister_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('DELETE FROM registrations WHERE user_id = ?', (user_id,))
        await db.commit()

async def get_user_profile(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            'SELECT nickname, photo_id FROM profiles WHERE user_id = ?',
            (user_id,)
        )
        return await cursor.fetchone()

# ==================== КЛАВИАТУРЫ ====================
def get_events_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for event_id, event_name in EVENTS.items():
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=event_name, callback_data=f"event_{event_id}")
        ])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel")])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")])
    return keyboard

def get_confirm_keyboard(event_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_participants_keyboard(event_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Посмотреть участников", callback_data=f"participants_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить ник", callback_data="edit_nickname")],
        [InlineKeyboardButton(text="📷 Изменить фото", callback_data="edit_photo")],
        [InlineKeyboardButton(text="📋 Мероприятия", callback_data="show_events")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def get_main_menu_keyboard():
    """Основное меню с кнопкой мероприятий"""
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Мероприятия")],
        [KeyboardButton(text="👤 Мой профиль")]
    ], resize_keyboard=True)

# ==================== ХЕНДЛЕРЫ ====================
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    
    if profile and profile[0]:
        await message.answer(
            f"👋 Привет, {profile[0]}!\n\nВыберите мероприятие для записи:",
            reply_markup=get_events_keyboard()
        )
    else:
        await message.answer(
            f"👋 Привет, {message.from_user.username}!\n\n"
            "Давай настроим твой профиль!\n\n"
            "Придумай себе никнейм (2-20 символов):",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
        )
        await state.set_state(ProfileSetup.waiting_for_nickname)

# ==================== НОВАЯ КОМАНДА /menu ====================
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    """Команда /menu доступна с любого шага"""
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    
    if profile and profile[0]:
        await message.answer(
            f"📋 **Мероприятия**\n\nВыберите мероприятие для записи:",
            parse_mode="Markdown",
            reply_markup=get_events_keyboard()
        )
    else:
        await message.answer(
            f"👋 Сначала настройте профиль!\n\n"
            "Придумай себе никнейм (2-20 символов):",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
        )
        await state.set_state(ProfileSetup.waiting_for_nickname)

# ==================== КНОПКА "📋 Мероприятия" ====================
@dp.message(F.text == "📋 Мероприятия")
async def btn_menu(message: types.Message, state: FSMContext):
    """Кнопка меню в чате"""
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    
    if profile and profile[0]:
        await message.answer(
            f"📋 **Мероприятия**\n\nВыберите мероприятие для записи:",
            parse_mode="Markdown",
            reply_markup=get_events_keyboard()
        )
    else:
        await message.answer(
            f"👋 Сначала настройте профиль!\n\n"
            "Придумай себе никнейм (2-20 символов):",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
        )
        await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.message(F.text == "👤 Мой профиль")
async def btn_profile(message: types.Message, state: FSMContext):
    """Кнопка профиля в чате"""
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    
    if profile and profile[0]:
        text = f"👤 **Ваш профиль**\n\n"
        text += f"Никнейм: {profile[0]}\n"
        text += f"Фото: {'✅ Загружено' if profile[1] else '❌ Не загружено'}\n\n"
        
        if profile[1]:
            try:
                await message.answer_photo(
                    photo=profile[1],
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=get_profile_keyboard()
                )
            except Exception:
                await message.answer(
                    text + "⚠️ Фото устарело, загрузите новое.",
                    parse_mode="Markdown",
                    reply_markup=get_profile_keyboard()
                )
        else:
            await message.answer(
                text,
                parse_mode="Markdown",
                reply_markup=get_profile_keyboard()
            )
    else:
        await message.answer(
            "Сначала настройте профиль! Нажмите /start",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📋 Мероприятия")]], resize_keyboard=True)
        )

@dp.message(ProfileSetup.waiting_for_nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Настройка отменена. Нажмите /start чтобы начать заново.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        return
    
    nickname = message.text.strip()
    if len(nickname) < 2 or len(nickname) > 20:
        await message.answer("Ник должен быть от 2 до 20 символов. Попробуй ещё раз:")
        return
    
    await state.update_data(nickname=nickname)
    await message.answer(
        f"Отлично! Твой ник: **{nickname}**\n\n"
        "Теперь отправь мне своё фото (как фотографию, не как файл):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⏭️ Пропустить")]], resize_keyboard=True)
    )
    await state.set_state(ProfileSetup.waiting_for_photo)

@dp.message(ProfileSetup.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    if message.text == "⏭️ Пропустить":
        data = await state.get_data()
        nickname = data.get("nickname", message.from_user.username)
        await save_profile(message.from_user.id, message.from_user.username, nickname, None)
        await state.clear()
        await message.answer(
            "Профиль создан! Теперь выбери мероприятие:",
            reply_markup=get_events_keyboard()
        )
        return
    
    if not message.photo:
        await message.answer("Это не фото! Отправь пожалуйста фотографию (или напиши '⏭️ Пропустить'):")
        return
    
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    nickname = data.get("nickname", message.from_user.username)
    
    await save_profile(message.from_user.id, message.from_user.username, nickname, photo_id)
    await state.clear()
    
    await message.answer(
        f"✅ Профиль готов!\n\nНик: {nickname}\n\nТеперь выбери мероприятие:",
        reply_markup=get_events_keyboard()
    )

@dp.callback_query(F.data.startswith("event_"))
async def select_event(callback: types.CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    
    registered = await check_user_registration(callback.from_user.id)
    
    if registered:
        if registered == event_id:
            await callback.answer("Вы уже записаны на это мероприятие!", show_alert=True)
            return
        else:
            await callback.answer("Сначала отмените текущую запись!", show_alert=True)
            return
    
    await callback.message.edit_text(
        f"📅 Вы выбрали: **{event_name}**\n\nПодтвердить участие?",
        parse_mode="Markdown",
        reply_markup=get_confirm_keyboard(event_id)
    )

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_registration(callback: types.CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    
    profile = await get_user_profile(callback.from_user.id)
    
    if not profile or not profile[0]:
        await callback.answer("Сначала настройте профиль! Нажмите /start", show_alert=True)
        return
    
    success = await register_for_event(callback.from_user.id, event_id)
    
    if success:
        await callback.message.edit_text(
            f"✅ **Вы записаны!**\n\nМероприятие: {event_name}\n\n"
            "Хотите посмотреть, кто ещё записался?",
            parse_mode="Markdown",
            reply_markup=get_participants_keyboard(event_id)
        )
    else:
        await callback.answer("Ошибка при записи. Попробуйте ещё раз.", show_alert=True)

@dp.callback_query(F.data.startswith("participants_"))
async def show_participants(callback: types.CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    
    participants = await get_event_participants(event_id)
    
    if participants:
        text = f"👥 **Участники: {event_name}**\n\n"
        text += f"**Всего участников: {len(participants)}**\n\n"
        
        text += "**Список участников:**\n"
        for i, (nickname, photo_id) in enumerate(participants, 1):
            text += f"{i}. {nickname}\n"
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к мероприятиям", callback_data="back")]
            ])
        )
        
        for i, (nickname, photo_id) in enumerate(participants, 1):
            if photo_id:
                try:
                    await callback.message.answer_photo(
                        photo=photo_id,
                        caption=f"#{i} {nickname}",
                        parse_mode="Markdown"
                    )
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logging.error(f"Failed to send photo for {nickname}: {e}")
                    await callback.message.answer(f"📷 {nickname} (фото недоступно)")
            else:
                await callback.message.answer(f"👤 {nickname} (без фото)")
    else:
        text = f"👥 **Участники: {event_name}**\n\n"
        text += "**Всего участников: 0**\n\n"
        text += "Пока никого нет. Будьте первым!"
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к мероприятиям", callback_data="back")]
            ])
        )

@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    profile = await get_user_profile(callback.from_user.id)
    
    if profile and profile[0]:
        text = f"👤 **Ваш профиль**\n\n"
        text += f"Никнейм: {profile[0]}\n"
        text += f"Фото: {'✅ Загружено' if profile[1] else '❌ Не загружено'}\n\n"
        
        if profile[1]:
            try:
                await callback.message.answer_photo(
                    photo=profile[1],
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=get_profile_keyboard()
                )
            except Exception as e:
                await callback.message.answer(
                    text + "⚠️ Фото устарело, загрузите новое.",
                    parse_mode="Markdown",
                    reply_markup=get_profile_keyboard()
                )
            await callback.message.delete()
        else:
            await callback.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=get_profile_keyboard()
            )
    else:
        await callback.answer("Сначала настройте профиль! Нажмите /start", show_alert=True)

@dp.callback_query(F.data == "edit_nickname")
async def edit_nickname(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Введите новый никнейм (2-20 символов):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    )
    await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.callback_query(F.data == "edit_photo")
async def edit_photo(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Отправьте новое фото (как фотографию, не как файл):",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    )
    await state.set_state(ProfileSetup.waiting_for_photo)

@dp.callback_query(F.data == "cancel")
async def cancel_registration(callback: types.CallbackQuery):
    await unregister_user(callback.from_user.id)
    await callback.message.edit_text(
        "❌ Ваша запись отменена.\n\nВыберите новое мероприятие:",
        reply_markup=get_events_keyboard()
    )

@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    registered = await check_user_registration(callback.from_user.id)
    
    if registered:
        event_name = EVENTS.get(registered)
        await callback.message.edit_text(
            f"✅ Вы записаны на: **{event_name}**\n\nВыберите действие:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Посмотреть участников", callback_data=f"participants_{registered}")],
                [InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel")],
                [InlineKeyboardButton(text="🔄 Выбрать другое", callback_data="show_events")]
            ])
        )
    else:
        await callback.message.edit_text(
            "Выберите мероприятие для записи:",
            reply_markup=get_events_keyboard()
        )

@dp.callback_query(F.data == "show_events")
async def show_events(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📋 **Мероприятия**\n\nВыберите мероприятие для записи:",
        parse_mode="Markdown",
        reply_markup=get_events_keyboard()
    )

# ==================== ЗАПУСК ====================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())