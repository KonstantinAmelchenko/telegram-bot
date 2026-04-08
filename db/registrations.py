import aiosqlite

from .identity import ensure_telegram_identity


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
