from aiogram import types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InputMediaPhoto
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    get_event_by_id
)
from keyboards import (
    get_events_keyboard,
    get_guests_keyboard,
    get_registered_keyboard,
    get_main_menu_keyboard,
    get_cancel_keyboard
)
from .profile import ProfileSetup


class EventRegistration(StatesGroup):
    waiting_for_guests = State()


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
async def select_event(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()  # ✅ Очищаем состояние при входе в мероприятие
    event_id = int(callback.data.split("_")[1])
    event = await get_event_by_id(event_id)
    if not event:
        await callback.answer("Мероприятие не найдено или удалено", show_alert=True)
        return

    _, event_name, event_date, event_time, event_address = event
    registered = await check_user_registration(callback.from_user.id, event_id)
    participants = await get_event_participants(event_id)

    text = f"**{event_name}**"
    if event_address:
        text += f". {event_address}\n"
    else:
        text += "\n"
    text += f"Дата: {event_date}\n"
    text += f"Время: {event_time}\n\n"

    if participants:
        text += "**Список участников:**\n"
        total = 0
        for i, (nickname, photo_id, guests) in enumerate(participants, 1):
            is_me = " (вы)" if nickname == callback.from_user.username else ""
            if guests > 0:
                text += f"{i}. {nickname} +{guests}{is_me}\n"
                total += guests
            else:
                text += f"{i}. {nickname}{is_me}\n"
            total += 1
        text += f"\n**Всего: {total} чел.**"
    else:
        text += "Пока никого нет. Будьте первым!"

    if registered:
        keyboard = get_registered_keyboard(event_id)
    else:
        keyboard = get_guests_keyboard(event_id)

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    photos_with_ids = [(nickname, photo_id) for nickname, photo_id, _ in participants if photo_id]
    photo_message_ids = []

    if photos_with_ids:
        for i in range(0, len(photos_with_ids), 10):
            batch = photos_with_ids[i:i+10]
            media_group = [InputMediaPhoto(media=photo_id) for _, photo_id in batch]
            try:
                result = await callback.message.answer_media_group(media=media_group)
                photo_message_ids.extend([msg.message_id for msg in result])
            except Exception as e:
                logging.error(f"Failed to send media group: {e}")

    await state.update_data(photo_message_ids=photo_message_ids)


@dp.callback_query(F.data.startswith("guests_"))
async def select_guests(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split("_")
    event_id = int(data[1])
    guests_count = int(data[2])
    
    await state.update_data(event_id=event_id, guests_count=guests_count)
    
    event = await get_event_by_id(event_id)
    if not event:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event_name = event[1]
    event_address = event[4]
    
    text = f"**{event_name}**"
    if event_address:
        text += f". {event_address}\n"
    else:
        text += "\n"
    text += f"Дата: {event[2]}\n"
    text += f"Время: {event[3]}\n\n"
    
    if guests_count > 0:
        text += f"👥 Вы записываетесь +{guests_count} гост(ей)\n\n"
    else:
        text += "👤 Вы записываетесь один\n\n"
    
    text += "**Подтвердить запись?**"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_register_{event_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"cancel_guests_{event_id}")]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_register_"))
async def confirm_register(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    guests_count = data.get("guests_count", 0)
    
    event = await get_event_by_id(event_id)
    if not event:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    event_name = event[1]
    event_address = event[4]
    success = await register_for_event(callback.from_user.id, event_id, guests_count)
    
    if success:
        participants = await get_event_participants(event_id)
        text = f"**{event_name}**"
        if event_address:
            text += f". {event_address}\n"
        else:
            text += "\n"
        text += f"Дата: {event[2]}\n"
        text += f"Время: {event[3]}\n\n"
        text += "**Список участников:**\n"
        
        total = 0
        for i, (nickname, photo_id, guests) in enumerate(participants, 1):
            is_me = " (вы)" if nickname == callback.from_user.username else ""
            if guests > 0:
                text += f"{i}. {nickname} +{guests}{is_me}\n"
                total += guests
            else:
                text += f"{i}. {nickname}{is_me}\n"
            total += 1
        
        text += f"\n**Всего: {total} чел.**"
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_registered_keyboard(event_id)
        )
        await callback.answer("✅ Вы записаны!")
    else:
        await callback.answer("❌ Ошибка при записи", show_alert=True)
    
    await state.clear()


@dp.callback_query(F.data.startswith("cancel_guests_"))
async def cancel_guests(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Отмена' при выборе гостей"""
    await state.clear()
    
    event_id = int(callback.data.split("_")[2])
    event = await get_event_by_id(event_id)
    
    if not event:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    
    _, event_name, event_date, event_time, event_address = event
    registered = await check_user_registration(callback.from_user.id, event_id)
    participants = await get_event_participants(event_id)
    
    text = f"**{event_name}**"
    if event_address:
        text += f". {event_address}\n"
    else:
        text += "\n"
    text += f"Дата: {event_date}\n"
    text += f"Время: {event_time}\n\n"
    
    if participants:
        text += "**Список участников:**\n"
        total = 0
        for i, (nickname, photo_id, guests) in enumerate(participants, 1):
            is_me = " (вы)" if nickname == callback.from_user.username else ""
            if guests > 0:
                text += f"{i}. {nickname} +{guests}{is_me}\n"
                total += guests
            else:
                text += f"{i}. {nickname}{is_me}\n"
            total += 1
        text += f"\n**Всего: {total} чел.**"
    else:
        text += "Пока никого нет. Будьте первым!"
    
    if registered:
        keyboard = get_registered_keyboard(event_id)
    else:
        keyboard = get_guests_keyboard(event_id)
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("unregister_"))
async def unregister_event(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[1])
    event = await get_event_by_id(event_id)
    if not event:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return

    event_name = event[1]
    event_address = event[4]
    success = await unregister_from_event(callback.from_user.id, event_id)

    if success:
        participants = await get_event_participants(event_id)
        text = f"**{event_name}**"
        if event_address:
            text += f". {event_address}\n"
        else:
            text += "\n"
        text += f"Дата: {event[2]}\n"
        text += f"Время: {event[3]}\n\n"
        text += "**Список участников:**\n"
        
        total = 0
        for i, (nickname, photo_id, guests) in enumerate(participants, 1):
            is_me = " (вы)" if nickname == callback.from_user.username else ""
            if guests > 0:
                text += f"{i}. {nickname} +{guests}{is_me}\n"
                total += guests
            else:
                text += f"{i}. {nickname}{is_me}\n"
            total += 1
        
        if participants:
            text += f"\n**Всего: {total} чел.**"
        else:
            text += "Пока никого нет."
        
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_guests_keyboard(event_id)
        )
        await callback.answer("✅ Вы отменили запись")
    else:
        await callback.answer("❌ Ошибка при отмене записи", show_alert=True)


@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    profile = await get_user_profile(callback.from_user.id)
    if profile and profile[0]:
        registrations = await check_user_registration(callback.from_user.id)
        event_counts = await get_all_event_counts()
        events = await get_all_events()
        await callback.message.edit_text(
            "📋 Мероприятия\n\nВыберите мероприятие:",
            parse_mode="Markdown",
            reply_markup=get_events_keyboard(registrations, event_counts, events)
        )
    else:
        await callback.message.edit_text(
            "Сначала настройте профиль! /start",
            reply_markup=get_cancel_keyboard()
        )
    await callback.answer()