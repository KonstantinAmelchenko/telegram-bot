from aiogram import types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto
import logging
from . import dp
from database import (
    get_user_profile,
    register_for_event,
    check_user_registration,
    unregister_from_event,
    get_event_participants,
    get_all_event_counts,
    get_all_events,
    get_event_by_id,
    get_day_of_week,
    format_event_date  # <-- Импортируем функцию
)
from keyboards import (
    get_events_keyboard,
    get_register_keyboard,
    get_registered_keyboard,
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
        event_counts = await get_all_event_counts()
        events = await get_all_events()
        await message.answer(
            f"👋 Привет, {profile[0]}!",
            reply_markup=get_events_keyboard(registrations, event_counts, events)
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
        event_counts = await get_all_event_counts()
        events = await get_all_events()
        await message.answer(
            "📋 Мероприятия\n\nВыберите мероприятие:",
            parse_mode="Markdown",
            reply_markup=get_events_keyboard(registrations, event_counts, events)
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
    event = await get_event_by_id(event_id)
    
    if not event:
        await callback.answer("Мероприятие не найдено или удалено", show_alert=True)
        return

    _, event_name, event_date, event_time = event
    day_of_week = get_day_of_week(event_date)
    formatted_date = format_event_date(event_date)  # <-- Форматируем дату
    
    registered = await check_user_registration(callback.from_user.id, event_id)
    participants = await get_event_participants(event_id)
    
    text = f"Играем в **{event_name}**\n"
    text += f"📅 **Дата:** {day_of_week}, {formatted_date}\n"  # <-- Используем форматированную дату
    text += f"⏰ **Время:** {event_time}\n\n"
    
    if participants:
        text += "**Список участников:**\n"
        for i, (nickname, photo_id) in enumerate(participants, 1):
            is_me = " (вы)" if nickname == callback.from_user.username else ""
            text += f"{i}. {nickname}{is_me}\n"
    else:
        text += "Пока никого нет. Будьте первым!"

    if registered:
        keyboard = get_registered_keyboard(event_id)
    else:
        keyboard = get_register_keyboard(event_id)

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    photos_with_ids = [(nickname, photo_id) for nickname, photo_id in participants if photo_id]
    if photos_with_ids:
        for i in range(0, len(photos_with_ids), 10):
            batch = photos_with_ids[i:i+10]
            media_group = [InputMediaPhoto(media=photo_id) for _, photo_id in batch]
            try:
                await callback.message.answer_media_group(media=media_group)
            except Exception as e:
                logging.error(f"Failed to send media group: {e}")

@dp.callback_query(F.data.startswith("register_"))
async def register_event(callback: types.CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    event = await get_event_by_id(event_id)
    
    if not event:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event_name = event[1]
    success = await register_for_event(callback.from_user.id, event_id)
    
    if success:
        participants = await get_event_participants(event_id)
        text = f"📅 **{event_name}**\n"
        text += f"🗓 **Дата:** {event[2]}\n"
        text += f"⏰ **Время:** {event[3]}\n\n"
        text += "**Список участников:**\n"
        for i, (nickname, photo_id) in enumerate(participants, 1):
            is_me = " (вы)" if nickname == callback.from_user.username else ""
            text += f"{i}. {nickname}{is_me}\n"
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_registered_keyboard(event_id))
        
        photos_with_ids = [(nickname, photo_id) for nickname, photo_id in participants if photo_id]
        if photos_with_ids:
            for i in range(0, len(photos_with_ids), 10):
                batch = photos_with_ids[i:i+10]
                media_group = [InputMediaPhoto(media=photo_id) for _, photo_id in batch]
                try:
                    await callback.message.answer_media_group(media=media_group)
                except Exception as e:
                    logging.error(f"Failed to send media group: {e}")
    else:
        await callback.answer("Вы уже записаны.", show_alert=True)

@dp.callback_query(F.data.startswith("unregister_"))
async def unregister_event(callback: types.CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    event = await get_event_by_id(event_id)
    
    if not event:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event_name = event[1]
    await unregister_from_event(callback.from_user.id, event_id)
    participants = await get_event_participants(event_id)
    
    text = f"📅 **{event_name}**\n"
    text += f"🗓 **Дата:** {event[2]}\n"
    text += f"⏰ **Время:** {event[3]}\n\n"
    
    if participants:
        text += "**Список участников:**\n"
        for i, (nickname, photo_id) in enumerate(participants, 1):
            is_me = " (вы)" if nickname == callback.from_user.username else ""
            text += f"{i}. {nickname}{is_me}\n"
    else:
        text += "Пока никого нет. Будьте первым!"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_register_keyboard(event_id))

@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    registrations = await check_user_registration(callback.from_user.id)
    event_counts = await get_all_event_counts()
    events = await get_all_events()
    await callback.message.edit_text(
        "📋 Афиша\n\nВыберите мероприятие:",
        parse_mode="Markdown",
        reply_markup=get_events_keyboard(registrations, event_counts, events)
    )

@dp.callback_query(F.data == "show_events")
async def show_events_from_profile(callback: types.CallbackQuery):
    registrations = await check_user_registration(callback.from_user.id)
    event_counts = await get_all_event_counts()
    events = await get_all_events()
    await callback.message.answer(
        "📋 **Мероприятия**\n\nВыберите мероприятие:",
        parse_mode="Markdown",
        reply_markup=get_events_keyboard(registrations, event_counts, events)
    )
    await callback.answer()