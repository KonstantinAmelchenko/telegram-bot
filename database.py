import aiosqlite
from datetime import datetime

def format_event_date(date_str: str) -> str:
    """Преобразует дату из DD.MM.YYYY в формат 'D месяц' (без года)"""
    try:
        day, month, year = map(int, date_str.split('.'))
        months = [
            'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
            'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
        ]
        return f"{day} {months[month - 1]}"
    except:
        return date_str

def get_day_of_week(date_str: str) -> str:
    """Возвращает полный день недели для даты в формате DD.MM.YYYY"""
    try:
        day, month, year = map(int, date_str.split('.'))
        date = datetime(year, month, day)
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        return days[date.weekday()]
    except:
        return ""

async def init_db():
    """Создаёт таблицы при первом запуске"""
    async with aiosqlite.connect("events.db") as db:
        # Таблица профилей
        await db.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            nickname TEXT,
            photo_id TEXT
        )
        ''')
        
        # Таблица регистраций
        await db.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_id INTEGER,
            UNIQUE(user_id, event_id)
        )
        ''')
        
        # Таблица мероприятий (ДОБАВЛЕНО поле address)
        await db.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
        ''')
        
        await db.commit()

async def save_profile(user_id: int, username: str, nickname: str, photo_id: str):
    async with aiosqlite.connect("events.db") as db:
        await db.execute(
            'INSERT OR REPLACE INTO profiles (user_id, username, nickname, photo_id) VALUES (?, ?, ?, ?)',
            (user_id, username, nickname, photo_id)
        )
        await db.commit()

async def get_user_profile(user_id: int):
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT nickname, photo_id FROM profiles WHERE user_id = ?',
            (user_id,)
        )
        return await cursor.fetchone()

async def register_for_event(user_id: int, event_id: int):
    async with aiosqlite.connect("events.db") as db:
        try:
            await db.execute(
                'INSERT INTO registrations (user_id, event_id) VALUES (?, ?)',
                (user_id, event_id)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def check_user_registration(user_id: int, event_id: int = None):
    async with aiosqlite.connect("events.db") as db:
        if event_id:
            cursor = await db.execute(
                'SELECT event_id FROM registrations WHERE user_id = ? AND event_id = ?',
                (user_id, event_id)
            )
        else:
            cursor = await db.execute(
                'SELECT event_id FROM registrations WHERE user_id = ?',
                (user_id,)
            )
        result = await cursor.fetchall()
        return [r[0] for r in result] if result else []

async def unregister_from_event(user_id: int, event_id: int):
    async with aiosqlite.connect("events.db") as db:
        await db.execute(
            'DELETE FROM registrations WHERE user_id = ? AND event_id = ?',
            (user_id, event_id)
        )
        await db.commit()

async def get_event_participants(event_id: int):
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute('''
        SELECT p.nickname, p.photo_id
        FROM registrations r
        JOIN profiles p ON r.user_id = p.user_id
        WHERE r.event_id = ?
        ''', (event_id,))
        return await cursor.fetchall()

async def get_all_event_counts():
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute('''
        SELECT event_id, COUNT(*) as count
        FROM registrations
        GROUP BY event_id
        ''')
        result = await cursor.fetchall()
        return {row[0]: row[1] for row in result}

# === ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ МЕРОПРИЯТИЯМИ ===

async def create_event(name: str, date: str, time: str, address: str = ""):
    """Создаёт новое мероприятие"""
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'INSERT INTO events (name, date, time, address) VALUES (?, ?, ?, ?)',
            (name, date, time, address)
        )
        await db.commit()
        return cursor.lastrowid

async def get_all_events():
    """Получает все активные мероприятия"""
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT id, name, date, time, address FROM events WHERE is_active = 1 ORDER BY date, time'
        )
        return await cursor.fetchall()

async def get_event_by_id(event_id: int):
    """Получает мероприятие по ID"""
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT id, name, date, time, address FROM events WHERE id = ? AND is_active = 1',
            (event_id,)
        )
        return await cursor.fetchone()

async def delete_event(event_id: int):
    """Удаляет (деактивирует) мероприятие"""
    async with aiosqlite.connect("events.db") as db:
        await db.execute(
            'UPDATE events SET is_active = 0 WHERE id = ?',
            (event_id,)
        )
        await db.commit()

async def get_event_count(event_id: int):
    """Получает количество участников конкретного мероприятия"""
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT COUNT(*) FROM registrations WHERE event_id = ?',
            (event_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0