from aiogram import types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from . import dp

from database import (
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
from .profile import ProfileSetup

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
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        registrations = await check_user_registration(message.from_user.id)
        await message.answer(
            "📋 **Мероприятия**\n\nВыберите мероприятие:",
            parse_mode="Markdown",
            reply_markup=get_events_keyboard(registrations)
        )
    else:
        await message.answer(
            "Сначала настройте профиль! /start",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.message(F.text == "📋 Мероприятия")
async def btn_menu(message: types.Message, state: FSMContext):
    await cmd_events(message, state)

@dp.callback_query(F.data.startswith("event_"))
async def select_event(callback: types.CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    registered = await check_user_registration(callback.from_user.id, event_id)
    
    if registered:
        await callback.message.edit_text(
            f"📅 **{event_name}**\n\n✅ Вы уже записаны!",
            parse_mode="Markdown",
            reply_markup=get_registered_keyboard(event_id)
        )
    else:
        await callback.message.edit_text(
            f"📅 **{event_name}**\n\nПодтвердить участие?",
            parse_mode="Markdown",
            reply_markup=get_confirm_keyboard(event_id)
        )

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_registration(callback: types.CallbackQuery):
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
    registrations = await check_user_registration(callback.from_user.id)
    await callback.message.edit_text(
        "📋 Афиша\n\nВыберите мероприятие:",
        parse_mode="Markdown",
        reply_markup=get_events_keyboard(registrations)
    )

@dp.callback_query(F.data == "show_events")  # ← Обработчик для кнопки из профиля
async def show_events(callback: types.CallbackQuery):
    registrations = await check_user_registration(callback.from_user.id)
    await callback.message.edit_text(
        "📋 **Мероприятия**\n\nВыберите мероприятие:",
        parse_mode="Markdown",
        reply_markup=get_events_keyboard(registrations)
    )