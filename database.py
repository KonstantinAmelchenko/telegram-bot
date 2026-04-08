import aiosqlite
import secrets
from datetime import datetime
from typing import Optional

def format_event_date(date_str: str) -> str:
    """Преобразует дату из DD.MM.YYYY в формат 'D месяц' (без года)"""
    try:
        day, month, year = map(int, date_str.split('.'))
        months = [
            'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
            'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
        ]
        return f"{day} {months[month - 1]}"
    except (ValueError, IndexError):
        return date_str

def get_day_of_week(date_str: str) -> str:
    """Возвращает полный день недели для даты в формате DD.MM.YYYY"""
    try:
        day, month, year = map(int, date_str.split('.'))
        date = datetime(year, month, day)
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        return days[date.weekday()]
    except (ValueError, IndexError):
        return ""

async def init_db():
    """Создаёт таблицы при первом запуске"""
    async with aiosqlite.connect("events.db") as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS app_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS telegram_accounts (
            telegram_user_id INTEGER PRIMARY KEY,
            app_user_id INTEGER NOT NULL,
            linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS vk_accounts (
            vk_user_id TEXT PRIMARY KEY,
            app_user_id INTEGER NOT NULL,
            linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS vk_link_tokens (
            token TEXT PRIMARY KEY,
            app_user_id INTEGER NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_id INTEGER,
            guests_count INTEGER DEFAULT 0,
            UNIQUE(user_id, event_id)
        )
        ''')
        
        # Добавляем колонку guests_count если её нет
        try:
            await db.execute('ALTER TABLE registrations ADD COLUMN guests_count INTEGER DEFAULT 0')
        except Exception:
            pass
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            address TEXT,
            max_people INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
        ''')

        # Добавляем колонку max_people если её нет
        try:
            await db.execute('ALTER TABLE events ADD COLUMN max_people INTEGER')
        except Exception:
            pass
        
        await db.commit()


async def _create_app_user(db: aiosqlite.Connection) -> int:
    cursor = await db.execute('INSERT INTO app_users DEFAULT VALUES')
    return cursor.lastrowid


async def _migrate_legacy_user_data(
    db: aiosqlite.Connection,
    legacy_user_id: int,
    app_user_id: int,
) -> None:
    """
    Переносит старые данные, где user_id == telegram_user_id, в app_user_id.
    Делается мягко и идемпотентно.
    """
    if legacy_user_id == app_user_id:
        return

    await db.execute(
        '''
        INSERT OR IGNORE INTO profiles (user_id, username, nickname, photo_id)
        SELECT ?, username, nickname, photo_id
        FROM profiles
        WHERE user_id = ?
        ''',
        (app_user_id, legacy_user_id)
    )

    await db.execute(
        '''
        INSERT INTO registrations (user_id, event_id, guests_count)
        SELECT ?, event_id, guests_count
        FROM registrations
        WHERE user_id = ?
        ON CONFLICT(user_id, event_id)
        DO UPDATE SET guests_count = MAX(registrations.guests_count, excluded.guests_count)
        ''',
        (app_user_id, legacy_user_id)
    )

    await db.execute(
        'DELETE FROM registrations WHERE user_id = ?',
        (legacy_user_id,)
    )
    await db.execute(
        'DELETE FROM profiles WHERE user_id = ?',
        (legacy_user_id,)
    )


async def get_app_user_id_by_telegram_id(telegram_user_id: int) -> Optional[int]:
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT app_user_id FROM telegram_accounts WHERE telegram_user_id = ?',
            (telegram_user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def get_app_user_id_by_vk_id(vk_user_id: str) -> Optional[int]:
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT app_user_id FROM vk_accounts WHERE vk_user_id = ?',
            (vk_user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def get_linked_accounts_by_app_user(app_user_id: int) -> tuple[Optional[int], Optional[str]]:
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            '''
            SELECT telegram_user_id
            FROM telegram_accounts
            WHERE app_user_id = ?
            LIMIT 1
            ''',
            (app_user_id,)
        )
        tg_row = await cursor.fetchone()

        cursor = await db.execute(
            '''
            SELECT vk_user_id
            FROM vk_accounts
            WHERE app_user_id = ?
            LIMIT 1
            ''',
            (app_user_id,)
        )
        vk_row = await cursor.fetchone()

        return (tg_row[0] if tg_row else None, vk_row[0] if vk_row else None)


async def ensure_telegram_identity(telegram_user_id: int) -> int:
    """Гарантирует связь Telegram аккаунта с внутренним app_user_id."""
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT app_user_id FROM telegram_accounts WHERE telegram_user_id = ?',
            (telegram_user_id,)
        )
        row = await cursor.fetchone()
        if row:
            await _migrate_legacy_user_data(db, telegram_user_id, row[0])
            await db.commit()
            return row[0]

        app_user_id = await _create_app_user(db)
        await db.execute(
            'INSERT INTO telegram_accounts (telegram_user_id, app_user_id) VALUES (?, ?)',
            (telegram_user_id, app_user_id)
        )
        await _migrate_legacy_user_data(db, telegram_user_id, app_user_id)
        await db.commit()
        return app_user_id


async def ensure_vk_identity(vk_user_id: str) -> int:
    """Гарантирует связь VK аккаунта с внутренним app_user_id."""
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT app_user_id FROM vk_accounts WHERE vk_user_id = ?',
            (vk_user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return row[0]

        app_user_id = await _create_app_user(db)
        await db.execute(
            'INSERT INTO vk_accounts (vk_user_id, app_user_id) VALUES (?, ?)',
            (vk_user_id, app_user_id)
        )
        await db.commit()
        return app_user_id


async def get_vk_user_id_by_telegram_id(telegram_user_id: int) -> Optional[str]:
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            '''
            SELECT v.vk_user_id
            FROM telegram_accounts t
            JOIN vk_accounts v ON v.app_user_id = t.app_user_id
            WHERE t.telegram_user_id = ?
            ''',
            (telegram_user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def get_telegram_user_id_by_vk_id(vk_user_id: str) -> Optional[int]:
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            '''
            SELECT t.telegram_user_id
            FROM vk_accounts v
            JOIN telegram_accounts t ON t.app_user_id = v.app_user_id
            WHERE v.vk_user_id = ?
            ''',
            (vk_user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def create_vk_link_token(vk_user_id: str, ttl_minutes: int = 10) -> str:
    """
    Создаёт одноразовый токен привязки VK -> Telegram.
    Этот метод удобно вызывать из backend VK Mini App.
    """
    app_user_id = await ensure_vk_identity(vk_user_id)
    async with aiosqlite.connect("events.db") as db:
        while True:
            token = secrets.token_urlsafe(24)
            try:
                await db.execute(
                    '''
                    INSERT INTO vk_link_tokens (token, app_user_id, expires_at)
                    VALUES (?, ?, datetime('now', ?))
                    ''',
                    (token, app_user_id, f"+{ttl_minutes} minutes")
                )
                await db.commit()
                return token
            except aiosqlite.IntegrityError:
                # Теоретически токен может совпасть, генерируем новый.
                continue


async def create_telegram_link_for_vk(vk_user_id: str, bot_username: str, ttl_minutes: int = 10) -> str:
    """
    Возвращает deep-link для кнопки "Привязать Telegram" в VK Mini App.
    Пример: https://t.me/<bot_username>?start=link_<token>
    """
    token = await create_vk_link_token(vk_user_id, ttl_minutes=ttl_minutes)
    normalized_bot_username = bot_username.strip().lstrip("@")
    return f"https://t.me/{normalized_bot_username}?start=link_{token}"


async def consume_vk_link_token(token: str, telegram_user_id: int) -> str:
    """
    Пытается привязать Telegram аккаунт к app_user по токену.
    Возвращает статус:
    - linked
    - already_linked
    - token_invalid
    - token_expired
    - token_used
    - telegram_linked_to_other
    - vk_already_has_telegram
    """
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT app_user_id, expires_at, used_at FROM vk_link_tokens WHERE token = ?',
            (token,)
        )
        token_row = await cursor.fetchone()
        if not token_row:
            return "token_invalid"

        target_app_user_id, expires_at, used_at = token_row
        if used_at is not None:
            return "token_used"

        cursor = await db.execute(
            "SELECT datetime(?) >= datetime('now')",
            (expires_at,)
        )
        is_not_expired = await cursor.fetchone()
        if not is_not_expired or not is_not_expired[0]:
            return "token_expired"

        cursor = await db.execute(
            'SELECT app_user_id FROM telegram_accounts WHERE telegram_user_id = ?',
            (telegram_user_id,)
        )
        tg_row = await cursor.fetchone()

        if tg_row and tg_row[0] != target_app_user_id:
            current_tg_app_user_id = tg_row[0]
            cursor = await db.execute(
                'SELECT 1 FROM vk_accounts WHERE app_user_id = ? LIMIT 1',
                (current_tg_app_user_id,)
            )
            has_vk_for_current_tg_app_user = await cursor.fetchone()
            if has_vk_for_current_tg_app_user:
                return "telegram_linked_to_other"

            # TG уже был создан отдельно (например, через /start), но еще не связан с VK.
            # Безопасно переносим TG связь на app_user из токена VK.
            await db.execute(
                'UPDATE telegram_accounts SET app_user_id = ? WHERE telegram_user_id = ?',
                (target_app_user_id, telegram_user_id)
            )
            await _migrate_legacy_user_data(db, telegram_user_id, target_app_user_id)
            tg_row = (target_app_user_id,)

        cursor = await db.execute(
            '''
            SELECT telegram_user_id
            FROM telegram_accounts
            WHERE app_user_id = ? AND telegram_user_id != ?
            ''',
            (target_app_user_id, telegram_user_id)
        )
        existing_tg_for_vk = await cursor.fetchone()
        if existing_tg_for_vk:
            return "vk_already_has_telegram"

        if not tg_row:
            await db.execute(
                'INSERT INTO telegram_accounts (telegram_user_id, app_user_id) VALUES (?, ?)',
                (telegram_user_id, target_app_user_id)
            )

        await db.execute(
            "UPDATE vk_link_tokens SET used_at = datetime('now') WHERE token = ?",
            (token,)
        )
        await db.commit()
        return "already_linked" if tg_row else "linked"


async def save_profile_by_app_user(app_user_id: int, username: str, nickname: str, photo_id: Optional[str]):
    async with aiosqlite.connect("events.db") as db:
        await db.execute(
            'INSERT OR REPLACE INTO profiles (user_id, username, nickname, photo_id) VALUES (?, ?, ?, ?)',
            (app_user_id, username, nickname, photo_id)
        )
        await db.commit()


async def get_user_profile_by_app_user(app_user_id: int):
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT nickname, photo_id FROM profiles WHERE user_id = ?',
            (app_user_id,)
        )
        return await cursor.fetchone()


async def register_for_event_by_app_user(app_user_id: int, event_id: int, guests_count: int = 0):
    async with aiosqlite.connect("events.db") as db:
        try:
            await db.execute(
                'INSERT INTO registrations (user_id, event_id, guests_count) VALUES (?, ?, ?)',
                (app_user_id, event_id, guests_count)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def check_user_registration_by_app_user(app_user_id: int, event_id: int = None):
    async with aiosqlite.connect("events.db") as db:
        if event_id:
            cursor = await db.execute(
                'SELECT event_id FROM registrations WHERE user_id = ? AND event_id = ?',
                (app_user_id, event_id)
            )
        else:
            cursor = await db.execute(
                'SELECT event_id FROM registrations WHERE user_id = ?',
                (app_user_id,)
            )
        result = await cursor.fetchall()
        return [r[0] for r in result] if result else []


async def unregister_from_event_by_app_user(app_user_id: int, event_id: int):
    async with aiosqlite.connect("events.db") as db:
        await db.execute(
            'DELETE FROM registrations WHERE user_id = ? AND event_id = ?',
            (app_user_id, event_id)
        )
        await db.commit()
        return True


async def save_profile(user_id: int, username: str, nickname: str, photo_id: str):
    app_user_id = await ensure_telegram_identity(user_id)
    await save_profile_by_app_user(app_user_id, username, nickname, photo_id)


async def get_user_profile(user_id: int):
    app_user_id = await ensure_telegram_identity(user_id)
    return await get_user_profile_by_app_user(app_user_id)


async def register_for_event(user_id: int, event_id: int, guests_count: int = 0):
    app_user_id = await ensure_telegram_identity(user_id)
    return await register_for_event_by_app_user(app_user_id, event_id, guests_count)


async def check_user_registration(user_id: int, event_id: int = None):
    app_user_id = await ensure_telegram_identity(user_id)
    return await check_user_registration_by_app_user(app_user_id, event_id)


async def unregister_from_event(user_id: int, event_id: int):
    app_user_id = await ensure_telegram_identity(user_id)
    return await unregister_from_event_by_app_user(app_user_id, event_id)

async def get_event_participants(event_id: int):
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute('''
        SELECT p.user_id, p.nickname, p.photo_id, r.guests_count
        FROM registrations r
        JOIN profiles p ON r.user_id = p.user_id
        WHERE r.event_id = ?
        ''', (event_id,))
        return await cursor.fetchall()

async def get_all_event_counts():
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute('''
        SELECT event_id, SUM(guests_count + 1) as count
        FROM registrations
        GROUP BY event_id
        ''')
        result = await cursor.fetchall()
        return {row[0]: row[1] for row in result}

async def create_event(name: str, date: str, time: str, address: str = "", max_people: int = None):
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'INSERT INTO events (name, date, time, address, max_people) VALUES (?, ?, ?, ?, ?)',
            (name, date, time, address, max_people)
        )
        await db.commit()
        return cursor.lastrowid

async def get_all_events():
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            '''
            SELECT id, name, date, time, address
            FROM events
            WHERE is_active = 1
            ORDER BY
                substr(date, 7, 4),
                substr(date, 4, 2),
                substr(date, 1, 2),
                time
            '''
        )
        return await cursor.fetchall()

async def get_event_by_id(event_id: int):
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT id, name, date, time, address, max_people FROM events WHERE id = ? AND is_active = 1',
            (event_id,)
        )
        return await cursor.fetchone()

async def delete_event(event_id: int):
    async with aiosqlite.connect("events.db") as db:
        await db.execute(
            'UPDATE events SET is_active = 0 WHERE id = ?',
            (event_id,)
        )
        await db.commit()

async def get_event_count(event_id: int):
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT COUNT(*) FROM registrations WHERE event_id = ?',
            (event_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0
