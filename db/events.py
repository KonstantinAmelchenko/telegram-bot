import aiosqlite


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
