from aiogram import types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

dp = Dispatcher(storage=MemoryStorage())

from database import (
    save_profile,
    get_user_profile,
    register_for_event,
    check_user_registration,
    unregister_from_event,
    get_event_participants
)
from keyboards import (
    EVENTS,
    get_events_keyboard,
    get_confirm_keyboard,
    get_registered_keyboard,
    get_participants_keyboard,
    get_main_menu_keyboard,
    get_cancel_keyboard
)

class ProfileSetup(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_photo = State()

# ==================== ХЕНДЛЕРЫ ====================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        registrations = await check_user_registration(message.from_user.id)
        await message.answer(
            f"👋 Привет, {profile[0]}!",
            reply_markup=get_events_keyboard(registrations)
        )
    else:
        await message.answer(
            "Придумай ник (2-20 символов):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.message(Command("events"))
async def cmd_events(message: types.Message, state: FSMContext):
    """Команда /events - доступна всегда"""
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        registrations = await check_user_registration(message.from_user.id)
        await message.answer(
            "📋 **Афиша**\n\nВыберите мероприятие:",
            parse_mode="Markdown",
            reply_markup=get_events_keyboard(registrations)
        )
    else:
        await message.answer(
            "Сначала настрой профиль! /start",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.message(F.text == "📋 Мероприятия")
async def btn_menu(message: types.Message, state: FSMContext):
    await cmd_events(message, state)

@dp.message(F.text == "👤 Профиль")
async def btn_profile(message: types.Message, state: FSMContext):
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        await message.answer(
            f"👤 **Ваш профиль**\n\nНик: {profile[0]}",
            parse_mode="Markdown",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer(
            "Настрой профиль! /start",
            reply_markup=get_main_menu_keyboard()
        )

@dp.message(ProfileSetup.waiting_for_nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено. /start")
        return
    nickname = message.text.strip()
    if len(nickname) < 2 or len(nickname) > 20:
        await message.answer("Ник от 2 до 20 символов:")
        return
    await state.update_data(nickname=nickname)
    await message.answer("Отправь фото или напиши 'Пропустить':")
    await state.set_state(ProfileSetup.waiting_for_photo)

@dp.message(ProfileSetup.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    if message.text == "Пропустить":
        data = await state.get_data()
        nickname = data.get("nickname", message.from_user.username)
        await save_profile(message.from_user.id, message.from_user.username, nickname, None)
        await state.clear()
        await message.answer("Профиль готов! /events", reply_markup=get_main_menu_keyboard())
        return
    if not message.photo:
        await message.answer("Это не фото! Отправь фотографию:")
        return
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    nickname = data.get("nickname", message.from_user.username)
    await save_profile(message.from_user.id, message.from_user.username, nickname, photo_id)
    await state.clear()
    await message.answer("✅ Профиль готов! /events", reply_markup=get_main_menu_keyboard())

@dp.callback_query(F.data.startswith("event_"))
async def select_event(callback: types.CallbackQuery):
    """Выбор мероприятия - показывает статус записи"""
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    registered = await check_user_registration(callback.from_user.id, event_id)
    
    if registered:
        # Уже записан - показываем кнопку отмены
        await callback.message.edit_text(
            f"📅 **{event_name}**\n\n✅ Вы уже записаны!",
            parse_mode="Markdown",
            reply_markup=get_registered_keyboard(event_id)
        )
    else:
        # Не записан - показываем кнопку подтверждения
        await callback.message.edit_text(
            f"📅 **{event_name}**\n\nПодтвердить участие?",
            parse_mode="Markdown",
            reply_markup=get_confirm_keyboard(event_id)
        )

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_registration(callback: types.CallbackQuery):
    """Подтверждение записи"""
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    success = await register_for_event(callback.from_user.id, event_id)
    if success:
        await callback.message.edit_text(
            f"✅ **Записаны!**\n\nМероприятие: {event_name}",
            parse_mode="Markdown",
            reply_markup=get_participants_keyboard(event_id)
        )
    else:
        await callback.answer("Вы уже записаны.", show_alert=True)

@dp.callback_query(F.data.startswith("unregister_"))
async def unregister_event(callback: types.CallbackQuery):
    """Отмена записи на конкретное мероприятие"""
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    await unregister_from_event(callback.from_user.id, event_id)
    await callback.message.edit_text(
        f"❌ **Отменено**\n\nМероприятие: {event_name}",
        parse_mode="Markdown",
        reply_markup=get_events_keyboard(await check_user_registration(callback.from_user.id))
    )

@dp.callback_query(F.data.startswith("participants_"))
async def show_participants(callback: types.CallbackQuery):
    """Список участников"""
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    participants = await get_event_participants(event_id)
    
    if participants:
        text = f"👥 **Участники: {event_name}**\n\n"
        text += f"**Всего: {len(participants)}**\n\n"
        for i, (nickname, photo_id) in enumerate(participants, 1):
            text += f"{i}. {nickname}\n"
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_participants_keyboard(event_id)
        )
    else:
        await callback.message.edit_text(
            f"👥 **{event_name}**\n\nПока никого нет!",
            parse_mode="Markdown",
            reply_markup=get_participants_keyboard(event_id)
        )

@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    """Назад к афише"""
    registrations = await check_user_registration(callback.from_user.id)
    await callback.message.edit_text(
        "📋 Афиша\n\nВыберите мероприятие:",
        parse_mode="Markdown",
        reply_markup=get_events_keyboard(registrations)
    )