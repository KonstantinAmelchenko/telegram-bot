import aiosqlite


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
