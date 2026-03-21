from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from . import dp

from database import save_profile, get_user_profile
from keyboards import get_profile_keyboard, get_main_menu_keyboard, get_cancel_keyboard, get_skip_keyboard

class ProfileSetup(StatesGroup):
    waiting_for_nickname = State()
    waiting_for_photo = State()

@dp.message(F.text == "👤 Профиль")
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
            reply_markup=get_main_menu_keyboard()
        )

@dp.message(ProfileSetup.waiting_for_nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    """Обработка ввода ника"""
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
        await message.answer(
            "Профиль создан! Теперь выберите мероприятие: /events",
            reply_markup=get_main_menu_keyboard()
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
        f"✅ Профиль готов!\n\nНик: {nickname}\n\nТеперь выберите мероприятие: /events",
        reply_markup=get_main_menu_keyboard()
    )

@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    """Показ профиля (inline)"""
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
            except Exception:
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
    """Редактирование ника"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Введите новый никнейм (2-20 символов):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ProfileSetup.waiting_for_nickname)

@dp.callback_query(F.data == "edit_photo")
async def edit_photo(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование фото"""
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Отправьте новое фото (как фотографию, не как файл):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ProfileSetup.waiting_for_photo)