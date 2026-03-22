from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID
from . import dp
from database import create_event, delete_event, get_all_events

class EventCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_address = State()

@dp.message(Command("create_event"))
async def cmd_create_event(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    await state.clear()
    await message.answer(
        "📝 **Создание мероприятия**\n\nВведите название:",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(EventCreation.waiting_for_name)

@dp.message(EventCreation.waiting_for_name)
async def process_event_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return
    
    await state.update_data(name=message.text)
    await message.answer("🗓 Введите дату (например, 25.05.2024):")
    await state.set_state(EventCreation.waiting_for_date)

@dp.message(EventCreation.waiting_for_date)
async def process_event_date(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return
    
    await state.update_data(date=message.text)
    await message.answer("⏰ Введите время (например, 14:00):")
    await state.set_state(EventCreation.waiting_for_time)

@dp.message(EventCreation.waiting_for_time)
async def process_event_time(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return
    
    await state.update_data(time=message.text)
    await message.answer("📍 Введите адрес (или '⏭️ Пропустить'):")
    await state.set_state(EventCreation.waiting_for_address)

@dp.message(EventCreation.waiting_for_address)
async def process_event_address(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=types.ReplyKeyboardRemove())
        return
    
    address = ""
    if message.text == "⏭️ Пропустить":
        address = ""
    else:
        address = message.text
    
    data = await state.get_data()
    event_id = await create_event(data['name'], data['date'], data['time'], address)
    
    await state.clear()
    await message.answer(
        f"✅ **Мероприятие создано!**\n\n"
        f"📅 {data['name']}\n"
        f"🗓 {data['date']}\n"
        f"⏰ {data['time']}\n"
        f"📍 {address if address else 'Адрес не указан'}\n\n"
        f"ID: {event_id}",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(Command("delete_event"))
async def cmd_delete_event(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    try:
        event_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /delete_event <ID>")
        return
    
    await delete_event(event_id)
    await message.answer(f"✅ Мероприятие {event_id} удалено.")

@dp.message(Command("list_events"))
async def cmd_list_events(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    events = await get_all_events()
    
    if not events:
        await message.answer("📭 Нет активных мероприятий.")
        return
    
    text = "📋 **Список мероприятий:**\n\n"
    for event_id, name, date, time, address in events:
        text += f"{event_id}. {name} | {date} {time}\n"
        if address:
            text += f"   📍 {address}\n"
    
    await message.answer(text, parse_mode="Markdown")