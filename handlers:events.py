import asyncio
import logging
from aiogram import types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from . import dp

from database import (
    get_user_profile,
    register_for_event,
    check_user_registration,
    unregister_user,
    get_event_participants
)
from keyboards import (
    EVENTS,
    get_events_keyboard,
    get_confirm_keyboard,
    get_participants_keyboard,
    get_main_menu_keyboard,
    get_cancel_keyboard
)
from .profile import ProfileSetup

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Команда /start"""
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        await message.answer(
            f"👋 Привет, {profile[0]}!\n\nВыберите мероприятие: /events",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await message.answer(
            f"👋 Привет, {message.from_user.username}!\n\n"
            "Давай настроим твой профиль!\n\n"
            "Придумай себе никнейм (2-20 символов):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    """Команда /menu"""
    await state.clear()
    await message.answer(
        "📋 **Главное меню**\n\n"
        "📋 Мероприятия - посмотреть афишу\n"
        "👤 Профиль - ваш профиль",
        parse_mode="Markdown",
        reply_markup=get_main_menu_keyboard()
    )

@dp.message(Command("events"))
async def cmd_events(message: types.Message, state: FSMContext):
    """Команда /events - показать мероприятия"""
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        await message.answer(
            "📋 **Афиша мероприятий**\n\nВыберите мероприятие для записи:",
            parse_mode="Markdown",
            reply_markup=get_events_keyboard()
        )
    else:
        await message.answer(
            "👋 Сначала настройте профиль!\n\n"
            "Придумай себе никнейм (2-20 символов):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.message(F.text == "📋 Мероприятия")
async def btn_menu(message: types.Message, state: FSMContext):
    """Кнопка меню в чате"""
    await cmd_events(message, state)

@dp.callback_query(F.data.startswith("event_"))
async def select_event(callback: types.CallbackQuery):
    """Выбор мероприятия"""
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    registered = await check_user_registration(callback.from_user.id)

    if registered:
        if registered == event_id:
            await callback.answer("Вы уже записаны!", show_alert=True)
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
    """Подтверждение записи"""
    event_id = int(callback.data.split("_")[1])
    event_name = EVENTS.get(event_id)
    profile = await get_user_profile(callback.from_user.id)

    if not profile or not profile[0]:
        await callback.answer("Сначала настройте профиль!", show_alert=True)
        return

    success = await register_for_event(callback.from_user.id, event_id)

    if success:
        await callback.message.edit_text(
            f"✅ **Вы записаны!**\n\nМероприятие: {event_name}\n\n"
            "Хотите посмотреть участников?",
            parse_mode="Markdown",
            reply_markup=get_participants_keyboard(event_id)
        )
    else:
        await callback.answer("Ошибка при записи.", show_alert=True)

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
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
            ])
        )
    else:
        await callback.message.edit_text(
            f"👥 **{event_name}**\n\nПока никого нет. Будьте первым!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
            ])
        )

@dp.callback_query(F.data == "cancel")
async def cancel_registration(callback: types.CallbackQuery):
    """Отмена записи"""
    await unregister_user(callback.from_user.id)
    await callback.message.edit_text(
        "❌ Запись отменена.\n\nВыберите мероприятие:",
        reply_markup=get_events_keyboard()
    )

@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery):
    """Назад к мероприятиям"""
    registered = await check_user_registration(callback.from_user.id)
    if registered:
        event_name = EVENTS.get(registered)
        await callback.message.edit_text(
            f"✅ Вы записаны на: **{event_name}**",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👥 Участники", callback_data=f"participants_{registered}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")],
                [InlineKeyboardButton(text="📋 Другое", callback_data="show_events")]
            ])
        )
    else:
        await callback.message.edit_text(
            "Выберите мероприятие:",
            reply_markup=get_events_keyboard()
        )

@dp.callback_query(F.data == "show_events")
async def show_events(callback: types.CallbackQuery):
    """Показать все мероприятия"""
    await callback.message.edit_text(
        "📋 Афиша\n\nВыберите мероприятие:",
        parse_mode="Markdown",
        reply_markup=get_events_keyboard()
    )