import re
from typing import Optional


HELP_TEXT = (
    "Доступные команды:\n"
    "• Мероприятия\n"
    "• Профиль\n"
    "• Привязать Telegram\n\n"
    "Текстовые команды:\n"
    "• мероприятие <ID>\n"
    "• записаться <ID> [гости]\n"
    "• отменить <ID>\n"
    "• ник <новый_ник>\n"
    "• фото (с прикрепленным изображением)\n\n"
    "Пример: записаться 12 2"
)


def normalize_text(text: Optional[str]) -> str:
    return (text or "").strip().lower()


def is_help_command(text: str) -> bool:
    return text in {"помощь", "help", "/help", "❓ помощь"}


def is_link_command(text: str) -> bool:
    commands = {
        "привязать telegram",
        "привязать телеграм",
        "привязать тг",
        "привязка",
        "link",
        "start",
        "/start",
        "🔗 привязать telegram",
    }
    return text in commands


def is_profile_command(text: str) -> bool:
    return text in {"профиль", "/profile", "👤 профиль"}


def is_events_command(text: str) -> bool:
    return text in {"мероприятия", "/events", "📋 мероприятия"}


def is_skip_command(text: str) -> bool:
    return text in {"пропустить", "skip", "⏭️ пропустить"}


def is_photo_command(text: str) -> bool:
    return text in {"фото", "photo", "обновить фото", "сменить фото"}


def parse_nick_command(text: str) -> Optional[str]:
    match = re.match(r"^ник\s+(.+)$", text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse_event_details_command(text: str) -> Optional[int]:
    match = re.match(r"^(мероприятие|event)\s+(\d+)$", text)
    return int(match.group(2)) if match else None


def parse_register_command(text: str) -> Optional[tuple[int, int]]:
    match = re.match(r"^(записаться|register)\s+(\d+)(?:\s+(\d+))?$", text)
    if not match:
        return None
    return int(match.group(2)), int(match.group(3) or 0)


def parse_unregister_command(text: str) -> Optional[int]:
    match = re.match(r"^(отменить|unregister)\s+(\d+)$", text)
    return int(match.group(2)) if match else None

