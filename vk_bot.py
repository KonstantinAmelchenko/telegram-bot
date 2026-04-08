import asyncio
import logging
import os
import re
import time
from typing import Optional

import vk_api
from dotenv import load_dotenv
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from database import (
    create_telegram_link_for_vk,
    ensure_vk_identity,
    get_telegram_user_id_by_vk_id,
    get_user_profile_by_app_user,
    init_db,
    register_for_event_by_app_user,
    save_profile_by_app_user,
    unregister_from_event_by_app_user,
)
from core import (
    HELP_TEXT,
    build_events_list_text,
    build_profile_text,
    get_event_view,
    has_profile,
    is_events_command,
    is_help_command,
    is_link_command,
    is_photo_command,
    is_profile_command,
    is_skip_command,
    normalize_text,
    parse_event_details_command,
    parse_nick_command,
    parse_register_command,
    parse_unregister_command,
    validate_nickname,
)


logging.basicConfig(level=logging.INFO)
load_dotenv()

VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME")
VK_API_VERSION = os.getenv("VK_API_VERSION", "5.199")

USER_STATES: dict[str, dict[str, str]] = {}


def build_main_keyboard() -> str:
    keyboard = VkKeyboard(one_time=False, inline=False)
    keyboard.add_button("📋 Мероприятия", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("👤 Профиль", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("🔗 Привязать Telegram", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("❓ Помощь", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def parse_group_id(raw_group_id: str) -> int:
    digits = re.sub(r"\D", "", raw_group_id or "")
    if not digits:
        raise ValueError("❌ VK_GROUP_ID должен содержать числовой id сообщества")
    return int(digits)


def extract_message_fields(event) -> tuple[str, Optional[int], Optional[int], int, list]:
    event_object = getattr(event, "object", None)
    message_obj = None

    if isinstance(event_object, dict):
        message_obj = event_object.get("message", event_object)
    elif hasattr(event_object, "message"):
        message_obj = getattr(event_object, "message")

    if not isinstance(message_obj, dict):
        return "", None, None, 0, []

    text_raw = message_obj.get("text", "") or ""
    from_id = message_obj.get("from_id") or message_obj.get("user_id")
    peer_id = message_obj.get("peer_id") or from_id
    is_outgoing = int(message_obj.get("out", 0) or 0)
    attachments = message_obj.get("attachments") or []
    return text_raw, from_id, peer_id, is_outgoing, attachments


def extract_group_name(groups_response) -> str:
    if isinstance(groups_response, list):
        if groups_response and isinstance(groups_response[0], dict):
            return groups_response[0].get("name", "unknown")
        return "unknown"

    if isinstance(groups_response, dict):
        groups_list = groups_response.get("groups")
        if isinstance(groups_list, list) and groups_list and isinstance(groups_list[0], dict):
            return groups_list[0].get("name", "unknown")
        return groups_response.get("name", "unknown")

    return "unknown"


def extract_photo_url(attachments: list) -> Optional[str]:
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        if attachment.get("type") != "photo":
            continue
        photo = attachment.get("photo")
        if not isinstance(photo, dict):
            continue
        sizes = photo.get("sizes") or []
        if not isinstance(sizes, list) or not sizes:
            continue
        best = max(
            (size for size in sizes if isinstance(size, dict)),
            key=lambda s: s.get("height", 0) * s.get("width", 0),
            default=None,
        )
        if best and best.get("url"):
            return best["url"]
    return None


async def build_link_message(vk_user_id: str) -> str:
    tg_user_id = await get_telegram_user_id_by_vk_id(vk_user_id)
    if tg_user_id:
        return (
            "✅ Telegram уже привязан.\n"
            f"ID Telegram: {tg_user_id}\n\n"
            "Если нужно перепривязать аккаунт, напишите администратору."
        )

    link = await create_telegram_link_for_vk(
        vk_user_id=vk_user_id,
        bot_username=TELEGRAM_BOT_USERNAME,
        ttl_minutes=10,
    )
    return (
        "🔗 Чтобы привязать Telegram:\n"
        "1. Нажмите на ссылку ниже.\n"
        "2. В Telegram откройте бота и нажмите Start.\n\n"
        f"{link}\n\n"
        "⏱ Ссылка действует 10 минут."
    )


async def build_event_details_message(app_user_id: int, event_id: int) -> str:
    view = await get_event_view(app_user_id, event_id)
    if not view:
        return "Мероприятие не найдено или удалено."
    if view.registered:
        hint = f"Для отмены: отменить {event_id}"
    else:
        hint = f"Для записи: записаться {event_id} [гости]"
    return f"{view.text_plain}\n\n{hint}"


async def handle_text_message(vk_user_id: str, text_raw: str, attachments: list) -> str:
    text = normalize_text(text_raw)
    app_user_id = await ensure_vk_identity(vk_user_id)
    state = USER_STATES.get(vk_user_id, {})
    photo_url = extract_photo_url(attachments)

    if state.get("mode") == "waiting_for_nickname":
        nickname = text_raw.strip()
        if not validate_nickname(nickname):
            return "Ник должен быть длиной от 2 до 20 символов. Попробуйте снова."
        await save_profile_by_app_user(app_user_id, f"vk_{vk_user_id}", nickname, None)
        USER_STATES[vk_user_id] = {"mode": "waiting_for_photo"}
        return (
            f"✅ Ник сохранен: {nickname}\n\n"
            "Теперь прикрепите фото профиля одним сообщением\n"
            "или напишите «пропустить»."
        )

    if state.get("mode") == "waiting_for_photo":
        profile = await get_user_profile_by_app_user(app_user_id)
        nickname = profile[0] if profile else f"vk_{vk_user_id}"
        if photo_url:
            await save_profile_by_app_user(app_user_id, f"vk_{vk_user_id}", nickname, photo_url)
            USER_STATES.pop(vk_user_id, None)
            return "✅ Фото профиля сохранено.\n\n" + await build_events_list_text(app_user_id)
        if is_skip_command(text):
            USER_STATES.pop(vk_user_id, None)
            return "Ок, без фото.\n\n" + await build_events_list_text(app_user_id)
        return "Не вижу фото. Прикрепите изображение или напишите «пропустить»."

    if state.get("mode") == "waiting_for_photo_update":
        profile = await get_user_profile_by_app_user(app_user_id)
        nickname = profile[0] if profile else f"vk_{vk_user_id}"
        if photo_url:
            await save_profile_by_app_user(app_user_id, f"vk_{vk_user_id}", nickname, photo_url)
            USER_STATES.pop(vk_user_id, None)
            return "✅ Фото профиля обновлено."
        if is_skip_command(text):
            USER_STATES.pop(vk_user_id, None)
            return "Обновление фото отменено."
        return "Прикрепите фото для обновления или напишите «пропустить»."

    nickname_command = parse_nick_command(text)
    if nickname_command:
        nickname = nickname_command
        if not validate_nickname(nickname):
            return "Ник должен быть длиной от 2 до 20 символов."
        profile = await get_user_profile_by_app_user(app_user_id)
        photo_id = profile[1] if profile else None
        await save_profile_by_app_user(app_user_id, f"vk_{vk_user_id}", nickname, photo_id)
        return f"✅ Ник обновлен: {nickname}"

    if is_link_command(text):
        return await build_link_message(vk_user_id)

    if is_help_command(text):
        return HELP_TEXT

    if is_profile_command(text):
        if not await has_profile(app_user_id):
            USER_STATES[vk_user_id] = {"mode": "waiting_for_nickname"}
            return "Профиль не настроен. Введите ник (2-20 символов):"
        return (
            await build_profile_text(app_user_id)
            + "\n\nЧтобы поменять ник: ник <новый_ник>\n"
            "Чтобы поменять фото: фото + вложение"
        )

    if is_photo_command(text):
        if not await has_profile(app_user_id):
            USER_STATES[vk_user_id] = {"mode": "waiting_for_nickname"}
            return "Сначала настройте профиль. Введите ник (2-20 символов):"
        if photo_url:
            profile = await get_user_profile_by_app_user(app_user_id)
            nickname = profile[0] if profile else f"vk_{vk_user_id}"
            await save_profile_by_app_user(app_user_id, f"vk_{vk_user_id}", nickname, photo_url)
            return "✅ Фото профиля обновлено."
        USER_STATES[vk_user_id] = {"mode": "waiting_for_photo_update"}
        return "Прикрепите фото следующим сообщением или напишите «пропустить»."

    if is_events_command(text):
        return await build_events_list_text(app_user_id)

    event_id = parse_event_details_command(text)
    if event_id is not None:
        return await build_event_details_message(app_user_id, event_id)

    register_data = parse_register_command(text)
    if register_data is not None:
        event_id, guests_count = register_data
        if guests_count < 0 or guests_count > 10:
            return "Количество гостей должно быть от 0 до 10."

        profile = await get_user_profile_by_app_user(app_user_id)
        if not profile or not profile[0]:
            USER_STATES[vk_user_id] = {"mode": "waiting_for_nickname"}
            return "Сначала настройте профиль. Введите ник (2-20 символов):"

        success = await register_for_event_by_app_user(app_user_id, event_id, guests_count)
        if not success:
            return "Вы уже записаны на это мероприятие."
        return "✅ Вы записаны.\n\n" + await build_event_details_message(app_user_id, event_id)

    event_id_to_cancel = parse_unregister_command(text)
    if event_id_to_cancel is not None:
        event_id = event_id_to_cancel
        await unregister_from_event_by_app_user(app_user_id, event_id)
        return "✅ Запись отменена.\n\n" + await build_event_details_message(app_user_id, event_id)

    if text in {"", "привет", "hello", "hi"}:
        if not await has_profile(app_user_id):
            USER_STATES[vk_user_id] = {"mode": "waiting_for_nickname"}
            return (
                "Привет! Чтобы начать, настройте профиль.\n"
                "Введите ник (2-20 символов):"
            )
        return "Привет! Выберите действие на клавиатуре или напишите «Помощь»."

    return "Команда не распознана. Напишите «Помощь» для списка команд."


async def async_setup() -> None:
    await init_db()


def main() -> None:
    if not VK_GROUP_TOKEN:
        raise ValueError("❌ Не указан VK_GROUP_TOKEN")
    if not VK_GROUP_ID:
        raise ValueError("❌ Не указан VK_GROUP_ID")
    if not TELEGRAM_BOT_USERNAME:
        raise ValueError("❌ Не указан TELEGRAM_BOT_USERNAME")

    asyncio.run(async_setup())
    keyboard = build_main_keyboard()

    vk_session = vk_api.VkApi(token=VK_GROUP_TOKEN, api_version=VK_API_VERSION)
    vk = vk_session.get_api()
    group_id = parse_group_id(VK_GROUP_ID)

    try:
        groups = vk.groups.getById(group_id=group_id)
        group_name = extract_group_name(groups)
        logging.info("VK API auth OK: group_id=%s group_name=%s", group_id, group_name)
    except Exception:
        logging.exception("VK API auth check failed")
        raise

    logging.info("VK bot started (group_id=%s)", group_id)

    while True:
        try:
            longpoll = VkBotLongPoll(vk_session, group_id=group_id)
            for event in longpoll.listen():
                if event.type != VkBotEventType.MESSAGE_NEW:
                    continue

                text_raw, from_id, peer_id, is_outgoing, attachments = extract_message_fields(event)
                if is_outgoing:
                    continue

                if not from_id or not peer_id:
                    logging.warning("Skip VK event with empty from_id/peer_id: %s", event.object)
                    continue

                user_id = str(from_id)
                logging.info("Incoming VK message: user_id=%s text=%s", user_id, text_raw)
                message = asyncio.run(handle_text_message(user_id, text_raw, attachments))

                try:
                    vk.messages.send(
                        peer_id=peer_id,
                        message=message,
                        random_id=int.from_bytes(os.urandom(4), byteorder="big"),
                        keyboard=keyboard,
                    )
                    logging.info("VK response sent: user_id=%s", user_id)
                except Exception:
                    logging.exception("Failed to send VK response: user_id=%s", user_id)
        except Exception:
            logging.exception("VK longpoll failed, reconnect in 3s")
            time.sleep(3)


if __name__ == "__main__":
    main()
