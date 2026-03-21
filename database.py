import aiosqlite
from config import DATABASE_URL

# ==================== ИНИЦИАЛИЗАЦИЯ БАЗЫ ====================
async def init_db():
    """Создаёт таблицы при первом запуске"""
    async with aiosqlite.connect("events.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                nickname TEXT,
                photo_id TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS registrations (
                user_id INTEGER PRIMARY KEY,
                event_id INTEGER
            )
        ''')
        await db.commit()

# ==================== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ====================
async def save_profile(user_id: int, username: str, nickname: str, photo_id: str):
    """Сохраняет или обновляет профиль"""
    async with aiosqlite.connect("events.db") as db:
        await db.execute(
            '''INSERT OR REPLACE INTO profiles (user_id, username, nickname, photo_id) 
               VALUES (?, ?, ?, ?)''',
            (user_id, username, nickname, photo_id)
        )
        await db.commit()

async def get_user_profile(user_id: int):
    """Получает профиль пользователя"""
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT nickname, photo_id FROM profiles WHERE user_id = ?',
            (user_id,)
        )
        return await cursor.fetchone()

# ==================== ЗАПИСЬ НА МЕРОПРИЯТИЯ ====================
async def register_for_event(user_id: int, event_id: int):
    """Записывает пользователя на событие"""
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

async def check_user_registration(user_id: int):
    """Проверяет, записан ли пользователь на событие"""
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT event_id FROM registrations WHERE user_id = ?',
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else None

async def unregister_user(user_id: int):
    """Отменяет запись на событие"""
    async with aiosqlite.connect("events.db") as db:
        await db.execute('DELETE FROM registrations WHERE user_id = ?', (user_id,))
        await db.commit()

# ==================== УЧАСТНИКИ ====================
async def get_event_participants(event_id: int):
    """Получает участников события с данными профиля"""
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute('''
            SELECT p.nickname, p.photo_id 
            FROM registrations r
            JOIN profiles p ON r.user_id = p.user_id
            WHERE r.event_id = ?
        ''', (event_id,))
        return await cursor.fetchall()