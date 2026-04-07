from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from . import dp
from database import (
    save_profile,
    get_user_profile,
    check_user_registration,
    get_all_event_counts,
    get_all_events,
    get_vk_user_id_by_telegram_id
)
from keyboards import (
    get_profile_keyboard,
    get_main_menu_keyboard,
    get_cancel_keyboard,
    get_skip_keyboard,
    get_events_keyboard
)


async def build_profile_text(telegram_user_id: int, nickname: str) -> str:
    vk_user_id = await get_vk_user_id_by_telegram_id(telegram_user_id)
    vk_status = f"✅ Привязан (ID: {vk_user_id})" if vk_user_id else "⬇️ Нажмите кнопку «Привязать VK»"
    return (
        f"Никнейм: {nickname}\n"
        f"Telegram: ✅ Привязан (ID: {telegram_user_id})\n"
        f"VK: {vk_status}"
    )


async def get_profile_markup(telegram_user_id: int):
    vk_user_id = await get_vk_user_id_by_telegram_id(telegram_user_id)
    return get_profile_keyboard(is_vk_linked=bool(vk_user_id))


@dp.message(Command("profile"))
async def cmd_profile(message: types.Message, state: FSMContext):
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        text = await build_profile_text(message.from_user.id, profile[0])
        profile_markup = await get_profile_markup(message.from_user.id)
        if profile[1]:
            try:
                await message.answer_photo(
                    photo=profile[1],
                    caption=text,
                    reply_markup=profile_markup
                )
            except Exception:
                await message.answer(
                    text + "\n⚠️ Фото устарело.",
                    reply_markup=profile_markup
                )
        else:
            await message.answer(
                text,
                reply_markup=profile_markup
            )
    else:
        await message.answer(
            "Сначала настройте профиль! Нажмите /start",
            reply_markup=get_main_menu_keyboard()
        )

class ProfileSetup(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_photo = State()
    editing_nickname = State()
    editing_photo = State()

@dp.message(F.text == "👤 Профиль")
async def btn_profile(message: types.Message, state: FSMContext):
    await state.clear()
    profile = await get_user_profile(message.from_user.id)
    if profile and profile[0]:
        text = await build_profile_text(message.from_user.id, profile[0])
        profile_markup = await get_profile_markup(message.from_user.id)
        if profile[1]:
            try:
                await message.answer_photo(
                    photo=profile[1],
                    caption=text,
                    reply_markup=profile_markup
                )
            except Exception:
                await message.answer(
                    text + "\n⚠️ Фото устарело.",
                    reply_markup=profile_markup
                )
        else:
            await message.answer(
                text,
                reply_markup=profile_markup
            )
    else:
        await message.answer(
            "Сначала настройте профиль! Нажмите /start",
            reply_markup=get_main_menu_keyboard()
        )

@dp.message(ProfileSetup.waiting_for_nickname)
async def process_nickname(message: types.Message, state: FSMContext):
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
        f"Отлично! Ник: {nickname}\n\nОтправь фото или '⏭️ Пропустить':",
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(ProfileSetup.waiting_for_photo)

@dp.message(ProfileSetup.editing_nickname)
async def process_edit_nickname(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_main_menu_keyboard())
        return
    nickname = message.text.strip()
    if len(nickname) < 2 or len(nickname) > 20:
        await message.answer("Ник от 2 до 20 символов:")
        return
    profile = await get_user_profile(message.from_user.id)
    old_photo_id = profile[1] if profile else None

    await save_profile(message.from_user.id, message.from_user.username, nickname, old_photo_id)
    await state.clear()

    await message.answer(
        f"✅ Ник изменён!\n\nНик: {nickname}",
        reply_markup=await get_profile_markup(message.from_user.id)
    )

@dp.message(ProfileSetup.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    if message.text == "⏭️ Пропустить":
        data = await state.get_data()
        nickname = data.get("nickname", message.from_user.username)
        await save_profile(message.from_user.id, message.from_user.username, nickname, None)
        await state.clear()
        await message.answer("✅ Профиль готов!", reply_markup=get_main_menu_keyboard())
        return
    if not message.photo:
        await message.answer("Это не фото! Отправь фотографию:")
        return
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    nickname = data.get("nickname", message.from_user.username)
    await save_profile(message.from_user.id, message.from_user.username, nickname, photo_id)
    await state.clear()
    await message.answer(f"✅ Профиль готов!\n\nНик: {nickname}", reply_markup=get_main_menu_keyboard())

@dp.message(ProfileSetup.editing_photo)
async def process_edit_photo(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_main_menu_keyboard())
        return
    if not message.photo:
        await message.answer("Это не фото! Отправь фотографию:")
        return
    profile = await get_user_profile(message.from_user.id)
    old_nickname = profile[0] if profile else message.from_user.username

    photo_id = message.photo[-1].file_id

    await save_profile(message.from_user.id, message.from_user.username, old_nickname, photo_id)
    await state.clear()

    await message.answer(
        f"✅ Фото изменено!\n\nНик: {old_nickname}",
        reply_markup=await get_profile_markup(message.from_user.id)
    )

@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    profile = await get_user_profile(callback.from_user.id)
    if profile and profile[0]:
        text = await build_profile_text(callback.from_user.id, profile[0])
        profile_markup = await get_profile_markup(callback.from_user.id)
        if profile[1]:
            try:
                await callback.message.answer_photo(
                    photo=profile[1],
                    caption=text,
                    reply_markup=profile_markup
                )
            except Exception:
                await callback.message.answer(
                    text + "\n⚠️ Фото устарело.",
                    reply_markup=profile_markup
                )
            await callback.message.delete()
        else:
            await callback.message.edit_text(
                text,
                reply_markup=profile_markup
            )
        await callback.answer()
    else:
        await callback.answer("Сначала настройте профиль! /start", show_alert=True)

@dp.callback_query(F.data == "edit_nickname")
async def edit_nickname(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("Введите новый ник (2-20 символов):", reply_markup=get_cancel_keyboard())
    await state.set_state(ProfileSetup.editing_nickname)

@dp.callback_query(F.data == "edit_photo")
async def edit_photo(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("Отправьте новое фото:", reply_markup=get_cancel_keyboard())
    await state.set_state(ProfileSetup.editing_photo)


@dp.callback_query(F.data == "link_vk_help")
async def link_vk_help(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "Чтобы привязать VK, откройте VK Mini App и нажмите кнопку привязки Telegram.\n"
        "После этого вернитесь в бота по ссылке из Mini App."
    )

@dp.callback_query(F.data == "show_events")
async def show_events_from_profile(callback: types.CallbackQuery):
    registrations = await check_user_registration(callback.from_user.id)
    event_counts = await get_all_event_counts()
    events = await get_all_events()
    events_text = "📋 **Мероприятия**\n\nВыберите мероприятие:"
    events_keyboard = get_events_keyboard(registrations, event_counts, events)
    try:
        await callback.message.edit_text(
            events_text,
            parse_mode="Markdown",
            reply_markup=events_keyboard
        )
    except TelegramBadRequest:
        # Если callback пришел из сообщения с фото, edit_text невозможен.
        await callback.message.answer(
            events_text,
            parse_mode="Markdown",
            reply_markup=events_keyboard
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
    await callback.answer()
