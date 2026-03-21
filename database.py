import aiosqlite

async def init_db():
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

async def save_profile(user_id, username, nickname, photo_id):
    async with aiosqlite.connect("events.db") as db:
        await db.execute(
            'INSERT OR REPLACE INTO profiles VALUES (?, ?, ?, ?)',
            (user_id, username, nickname, photo_id)
        )
        await db.commit()

async def get_user_profile(user_id):
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT nickname, photo_id FROM profiles WHERE user_id = ?',
            (user_id,)
        )
        return await cursor.fetchone()

async def register_for_event(user_id, event_id):
    async with aiosqlite.connect("events.db") as db:
        try:
            await db.execute(
                'INSERT INTO registrations VALUES (?, ?)',
                (user_id, event_id)
            )
            await db.commit()
            return True
        except:
            return False

async def check_user_registration(user_id):
    async with aiosqlite.connect("events.db") as db:
        cursor = await db.execute(
            'SELECT event_id FROM registrations WHERE user_id = ?',
            (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else None

async def unregister_user(user_id):
    async with aiosqlite.connect("events.db") as db:
        await db.execute('DELETE FROM registrations WHERE user_id = ?', (user_id,))
        await db.commit()