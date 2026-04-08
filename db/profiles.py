from typing import Optional

import aiosqlite

from .identity import ensure_telegram_identity


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


async def save_profile(user_id: int, username: str, nickname: str, photo_id: str):
    app_user_id = await ensure_telegram_identity(user_id)
    await save_profile_by_app_user(app_user_id, username, nickname, photo_id)


async def get_user_profile(user_id: int):
    app_user_id = await ensure_telegram_identity(user_id)
    return await get_user_profile_by_app_user(app_user_id)
