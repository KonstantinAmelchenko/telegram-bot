from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from . import dp

from database import save_profile, get_user_profile, check_user_registration
from keyboards import (
    get_profile_keyboard,
    get_main_menu_keyboard,
    get_cancel_keyboard,
    get_skip_keyboard,
    get_events_keyboard
)

class ProfileSetup(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_photo = State()

@dp.message(F.text == "👤 Профиль")
async def btn_profile(message: types.Message, state: FSMContext):
    """Кнопка профиля в чате"""
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        text = f"Никнейм: {profile[0]}"
        
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
                    text + "\n⚠️ Фото устарело.",
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
            reply_markup=get_main_menu_keyboard()
        )

@dp.message(ProfileSetup.waiting_for_nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    """Обработка ввода ника"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено. /start", reply_markup=types.ReplyKeyboardRemove())
        return
    nickname = message.text.strip()
    if len(nickname) < 2 or len(nickname) > 20:
        await message.answer("Ник от 2 до 20 символов:")
        return
    await state.update_data(nickname=nickname)
    await message.answer(
        f"Отлично! Ник: **{nickname}**\n\nОтправь фото или '⏭️ Пропустить':",
        parse_mode="Markdown",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(ProfileSetup.waiting_for_photo)

@dp.message(ProfileSetup.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    """Обработка загрузки фото"""
    if message.text == "⏭️ Пропустить":
        data = await state.get_data()
        nickname = data.get("nickname", message.from_user.username)
        await save_profile(message.from_user.id, message.from_user.username, nickname, None)
        await state.clear()
        await message.answer("✅ Профиль готов!", reply_markup=get_events_keyboard())
        return
    if not message.photo:
        await message.answer("Это не фото! Отправь фотографию:")
        return
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    nickname = data.get("nickname", message.from_user.username)
    await save_profile(message.from_user.id, message.from_user.username, nickname, photo_id)
    await state.clear()
    await message.answer(f"✅ Профиль готов!\n\nНик: {nickname}", reply_markup=get_events_keyboard())

@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    """Показ профиля (inline)"""
    profile = await get_user_profile(callback.from_user.id)
    if profile and profile[0]:
        text = f"Никнейм: {profile[0]}"
        
        if profile[1]:
            try:
                await callback.message.answer_photo(
                    photo=profile[1],
                    caption=text,
                    parse_mode="Markdown",
                    reply_markup=get_profile_keyboard()
                )
            except Exception:
                await callback.message.answer(
                    text + "\n⚠️ Фото устарело.",
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
        await callback.answer("Сначала настройте профиль! /start", show_alert=True)

@dp.callback_query(F.data == "edit_nickname")
async def edit_nickname(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование ника"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Введите новый ник (2-20 символов):", reply_markup=get_cancel_keyboard())
    await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.callback_query(F.data == "edit_photo")
async def edit_photo(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование фото"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Отправьте новое фото:", reply_markup=get_cancel_keyboard())
    await state.set_state(ProfileSetup.waiting_for_photo)

@dp.callback_query(F.data == "show_events")
async def show_events_from_profile(callback: types.CallbackQuery):
    """Кнопка Мероприятия из профиля — отправляем НОВОЕ сообщение, фото не трогаем"""
    registrations = await check_user_registration(callback.from_user.id)
    
    # Просто отправляем новое сообщение с мероприятиями
    # Фото профиля остаётся на месте
    await callback.message.answer(
        "📋 **Мероприятия**\n\nВыберите мероприятие:",
        parse_mode="Markdown",
        reply_markup=get_events_keyboard(registrations)
    )
    
    # Убираем "часы" (loading state) у кнопки
    await callback.answer()