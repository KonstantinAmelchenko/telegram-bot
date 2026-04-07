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
    get_telegram_user_id_by_vk_id,
    init_db,
)


logging.basicConfig(level=logging.INFO)
load_dotenv()

VK_GROUP_TOKEN = os.getenv("VK_GROUP_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME")
VK_API_VERSION = os.getenv("VK_API_VERSION", "5.199")


def build_main_keyboard() -> str:
    keyboard = VkKeyboard(one_time=False, inline=False)
    keyboard.add_button("Привязать Telegram", color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()


def normalize_text(text: Optional[str]) -> str:
    return (text or "").strip().lower()


def is_link_command(text: str) -> bool:
    commands = {
        "привязать telegram",
        "привязать телеграм",
        "привязать тг",
        "привязка",
        "link",
        "start",
        "/start",
    }
    return text in commands


def parse_group_id(raw_group_id: str) -> int:
    digits = re.sub(r"\D", "", raw_group_id or "")
    if not digits:
        raise ValueError("❌ VK_GROUP_ID должен содержать числовой id сообщества")
    return int(digits)


def extract_message_fields(event) -> tuple[str, Optional[int], Optional[int], int]:
    event_object = getattr(event, "object", None)
    message_obj = None

    if isinstance(event_object, dict):
        message_obj = event_object.get("message", event_object)
    elif hasattr(event_object, "message"):
        message_obj = getattr(event_object, "message")

    if not isinstance(message_obj, dict):
        return "", None, None, 0

    text_raw = message_obj.get("text", "") or ""
    from_id = message_obj.get("from_id") or message_obj.get("user_id")
    peer_id = message_obj.get("peer_id") or from_id
    is_outgoing = int(message_obj.get("out", 0) or 0)
    return text_raw, from_id, peer_id, is_outgoing


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
        group_name = groups[0].get("name", "unknown") if groups else "unknown"
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

                text_raw, from_id, peer_id, is_outgoing = extract_message_fields(event)
                if is_outgoing:
                    continue

                if not from_id or not peer_id:
                    logging.warning("Skip VK event with empty from_id/peer_id: %s", event.object)
                    continue

                text = normalize_text(text_raw)
                user_id = str(from_id)
                logging.info("Incoming VK message: user_id=%s text=%s", user_id, text_raw)

                if is_link_command(text):
                    message = asyncio.run(build_link_message(user_id))
                else:
                    message = (
                        "Привет! Нажмите кнопку «Привязать Telegram», чтобы связать аккаунты."
                    )

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
