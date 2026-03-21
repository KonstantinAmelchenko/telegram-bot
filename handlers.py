from aiogram import types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

dp = Dispatcher(storage=MemoryStorage())

from database import save_profile, get_user_profile, register_for_event, check_user_registration, unregister_from_event, get_event_participants
from keyboards import EVENTS, get_events_keyboard, get_confirm_keyboard, get_main_menu_keyboard, get_cancel_keyboard

class ProfileSetup(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_photo = State()

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        await message.answer(f"Привет, {profile[0]}!", reply_markup=get_events_keyboard())
    else:
        await message.answer("Придумай ник (2-20 символов):", reply_markup=get_cancel_keyboard())
        await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.message(F.text == "📋 Мероприятия")
async def btn_menu(message: types.Message, state: FSMContext):
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        await message.answer("Выберите мероприятие:", reply_markup=get_events_keyboard())
    else:
        await message.answer("Сначала настрой профиль! /start", reply_markup=get_cancel_keyboard())
        await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.message(F.text == "👤 Профиль")
async def btn_profile(message: types.Message, state: FSMContext):
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        await message.answer(f"Ник: {profile[0]}", reply_markup=get_events_keyboard())
    else:
        await message.answer("Настрой профиль! /start", reply_markup=get_main_menu_keyboard())

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
    data = await state.get_data()
    nickname = data.get("nickname", message.from_user.username)
    photo_id = message.photo[-1].file_id if message.photo else None
    await save_profile(message.from_user.id, message.from_user.username, nickname, photo_id)
    await state.clear()
    await message.answer("Готово! Выбери мероприятие:", reply_markup=get_events_keyboard())

@dp.callback_query(F.data.startswith("event_"))
async def select_event(callback: types.CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    registered = await check_user_registration(callback.from_user.id)
    if registered:
        await callback.answer("Вы уже записаны!", show_alert=True)
        return
    await callback.message.edit_text(f"Выбрано: {event_name}\nПодтвердить?", reply_markup=get_confirm_keyboard(event_id))

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_registration(callback: types.CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    success = await register_for_event(callback.from_user.id, event_id)
    if success:
        await callback.message.edit_text(f"✅ Записан: {event_name}")
    else:
        await callback.answer("Ошибка", show_alert=True)

@dp.callback_query(F.data == "cancel")
async def cancel_registration(callback: types.CallbackQuery):
    """Отмена записи"""
    registered = await check_user_registration(callback.from_user.id)
    if registered:
        event_id = registered[0] if isinstance(registered, list) else registered
        await unregister_from_event(callback.from_user.id, event_id)
    await callback.message.edit_text(
        "❌ Ваша запись отменена.\n\nВыберите новое мероприятие:",
        reply_markup=get_events_keyboard()
    )

@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    await callback.message.edit_text("Выберите мероприятие:", reply_markup=get_events_keyboard())