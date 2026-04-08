import secrets
from typing import Optional

import aiosqlite


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
