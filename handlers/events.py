from aiogram import types, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InputMediaPhoto
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from html import escape
import logging
from . import dp
from database import (
    consume_vk_link_token,
    ensure_telegram_identity,
    register_for_event_by_app_user,
    unregister_from_event_by_app_user,
)
from core import (
    HELP_TEXT,
    get_event_view,
    get_events_menu_payload,
    is_help_command,
    parse_event_details_command,
    parse_register_command,
    parse_unregister_command,
)
from keyboards import (
    get_events_keyboard,
    get_guests_keyboard,
    get_registered_keyboard,
    get_cancel_keyboard
)
from .profile import ProfileSetup


class EventRegistration(StatesGroup):
    waiting_for_guests = State()


@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, command: CommandObject):
    await state.clear()
    app_user_id = await ensure_telegram_identity(message.from_user.id)

    if command.args and command.args.startswith("link_"):
        token = command.args[5:].strip()
        if token:
            link_status = await consume_vk_link_token(token, message.from_user.id)
            if link_status in {"linked", "already_linked"}:
                await message.answer("✅ Аккаунт VK успешно привязан.")
            elif link_status == "token_expired":
                await message.answer("⏱ Ссылка для привязки истекла. Запросите новую в VK Mini App.")
            elif link_status == "token_used":
                await message.answer("⚠️ Эта ссылка уже использована. Запросите новую в VK Mini App.")
            elif link_status == "telegram_linked_to_other":
                await message.answer("⚠️ Этот Telegram уже привязан к другому VK аккаунту.")
            elif link_status == "vk_already_has_telegram":
                await message.answer("⚠️ Этот VK аккаунт уже привязан к другому Telegram.")
            else:
                await message.answer("❌ Ссылка для привязки недействительна.")

    events_payload = await get_events_menu_payload(app_user_id)
    if events_payload["has_profile"]:
        await message.answer(
            f"👋 Привет, {events_payload['nickname']}!",
            reply_markup=get_events_keyboard(
                events_payload["registrations"],
                events_payload["event_counts"],
                events_payload["events"],
            )
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
    app_user_id = await ensure_telegram_identity(message.from_user.id)
    events_payload = await get_events_menu_payload(app_user_id)
    if events_payload["has_profile"]:
        await message.answer(
            "📋 Мероприятия\n\nВыберите мероприятие:",
            parse_mode="Markdown",
            reply_markup=get_events_keyboard(
                events_payload["registrations"],
                events_payload["event_counts"],
                events_payload["events"],
            )
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


@dp.message(F.text)
async def text_commands_router(message: types.Message, state: FSMContext):
    text = (message.text or "").strip().lower()
    if not text:
        return

    if is_help_command(text):
        await state.clear()
        await message.answer(HELP_TEXT)
        return

    app_user_id = await ensure_telegram_identity(message.from_user.id)

    event_id = parse_event_details_command(text)
    if event_id is not None:
        await state.clear()
        event_view = await get_event_view(app_user_id, event_id)
        if not event_view:
            await message.answer("Мероприятие не найдено или удалено.")
            return
        markup = get_registered_keyboard(event_id) if event_view.registered else get_guests_keyboard(event_id)
        await message.answer(event_view.text_html, parse_mode="HTML", reply_markup=markup)
        return

    register_data = parse_register_command(text)
    if register_data is not None:
        await state.clear()
        event_id, guests_count = register_data
        if guests_count < 0 or guests_count > 10:
            await message.answer("Количество гостей должно быть от 0 до 10.")
            return
        event_view = await get_event_view(app_user_id, event_id)
        if not event_view:
            await message.answer("Мероприятие не найдено или удалено.")
            return
        success = await register_for_event_by_app_user(app_user_id, event_id, guests_count)
        if not success:
            await message.answer("Вы уже записаны на это мероприятие.")
            return
        updated = await get_event_view(app_user_id, event_id)
        if not updated:
            await message.answer("Мероприятие не найдено или удалено.")
            return
        await message.answer(updated.text_html, parse_mode="HTML", reply_markup=get_registered_keyboard(event_id))
        return

    unregister_event_id = parse_unregister_command(text)
    if unregister_event_id is not None:
        await state.clear()
        event_view = await get_event_view(app_user_id, unregister_event_id)
        if not event_view:
            await message.answer("Мероприятие не найдено или удалено.")
            return
        await unregister_from_event_by_app_user(app_user_id, unregister_event_id)
        updated = await get_event_view(app_user_id, unregister_event_id)
        if not updated:
            await message.answer("Мероприятие не найдено или удалено.")
            return
        await message.answer(
            updated.text_html,
            parse_mode="HTML",
            reply_markup=get_guests_keyboard(unregister_event_id),
        )
        return


@dp.callback_query(F.data.startswith("event_"))
async def select_event(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    app_user_id = await ensure_telegram_identity(callback.from_user.id)
    event_id = int(callback.data.split("_")[1])
    event_view = await get_event_view(app_user_id, event_id)
    if not event_view:
        await callback.answer("Мероприятие не найдено или удалено", show_alert=True)
        return

    if event_view.registered:
        keyboard = get_registered_keyboard(event_id)
    else:
        keyboard = get_guests_keyboard(event_id)

    await callback.message.edit_text(
        event_view.text_html,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    photos_with_ids = [(nickname, photo_id) for _, nickname, photo_id, _ in event_view.participants if photo_id]
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
    await callback.answer()


@dp.callback_query(F.data.startswith("guests_"))
async def select_guests(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split("_")
    event_id = int(data[1])
    guests_count = int(data[2])
    await state.update_data(event_id=event_id, guests_count=guests_count)

    event_view = await get_event_view(app_user_id=await ensure_telegram_identity(callback.from_user.id), event_id=event_id)
    if not event_view:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return

    text = f"<b>{escape(event_view.name)}</b>"
    if event_view.address:
        text += f". {escape(event_view.address)}\n"
    else:
        text += "\n"
    text += f"Дата: {escape(event_view.date)}\n"
    text += f"Время: {escape(event_view.time)}\n"
    limit_text = str(event_view.max_people) if event_view.max_people and event_view.max_people > 0 else "не указано"
    text += f"<b>Зарегистрировано: {event_view.total_registered} из {limit_text}</b>\n\n"

    if guests_count > 0:
        text += f"👥 Вы записываетесь +{guests_count} гост(ей)\n\n"
    else:
        text += "👤 Вы записываетесь один\n\n"

    text += "<b>Подтвердить запись?</b>"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_register_{event_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_register_"))
async def confirm_register(callback: types.CallbackQuery, state: FSMContext):
    app_user_id = await ensure_telegram_identity(callback.from_user.id)
    event_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    guests_count = data.get("guests_count", 0)
    if not await get_event_view(app_user_id, event_id):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return

    success = await register_for_event_by_app_user(app_user_id, event_id, guests_count)

    if success:
        event_view = await get_event_view(app_user_id, event_id)
        if not event_view:
            await callback.answer("Мероприятие не найдено", show_alert=True)
            await state.clear()
            return

        await callback.message.edit_text(
            event_view.text_html,
            parse_mode="HTML",
            reply_markup=get_registered_keyboard(event_id)
        )
        await callback.answer("✅ Вы записаны!")
    else:
        await callback.answer("❌ Ошибка при записи", show_alert=True)

    await state.clear()

@dp.callback_query(F.data.startswith("unregister_"))
async def unregister_event(callback: types.CallbackQuery, state: FSMContext):
    app_user_id = await ensure_telegram_identity(callback.from_user.id)
    event_id = int(callback.data.split("_")[1])
    if not await get_event_view(app_user_id, event_id):
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return

    success = await unregister_from_event_by_app_user(app_user_id, event_id)

    if success:
        event_view = await get_event_view(app_user_id, event_id)
        if not event_view:
            await callback.answer("Мероприятие не найдено", show_alert=True)
            return

        await callback.message.edit_text(
            event_view.text_html,
            parse_mode="HTML",
            reply_markup=get_guests_keyboard(event_id)
        )
        await callback.answer("✅ Вы отменили запись")
    else:
        await callback.answer("❌ Ошибка при отмене записи", show_alert=True)


@dp.callback_query(F.data == "back")
async def go_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    app_user_id = await ensure_telegram_identity(callback.from_user.id)
    events_payload = await get_events_menu_payload(app_user_id)
    if events_payload["has_profile"]:
        await callback.message.edit_text(
            "📋 Мероприятия\n\nВыберите мероприятие:",
            parse_mode="Markdown",
            reply_markup=get_events_keyboard(
                events_payload["registrations"],
                events_payload["event_counts"],
                events_payload["events"],
            )
        )
    else:
        await callback.message.edit_text(
            "Сначала настройте профиль! /start",
            reply_markup=get_cancel_keyboard()
        )
    await callback.answer()
