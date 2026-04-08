from dataclasses import dataclass
from html import escape
from typing import Optional

from database import (
    check_user_registration_by_app_user,
    format_event_date,
    get_all_event_counts,
    get_all_events,
    get_day_of_week,
    get_event_by_id,
    get_event_participants,
    get_linked_accounts_by_app_user,
    get_user_profile_by_app_user,
)


@dataclass
class EventView:
    event_id: int
    name: str
    date: str
    time: str
    address: str
    max_people: int
    total_registered: int
    registered: bool
    participants: list
    text_html: str
    text_plain: str


def validate_nickname(nickname: str) -> bool:
    value = (nickname or "").strip()
    return 2 <= len(value) <= 20


async def has_profile(app_user_id: int) -> bool:
    profile = await get_user_profile_by_app_user(app_user_id)
    return bool(profile and profile[0])


async def build_profile_text(app_user_id: int) -> str:
    profile = await get_user_profile_by_app_user(app_user_id)
    nickname = profile[0] if profile else None
    if not nickname:
        return ""

    telegram_user_id, vk_user_id = await get_linked_accounts_by_app_user(app_user_id)
    tg_status = f"✅ Привязан (ID: {telegram_user_id})" if telegram_user_id else "❌ Не привязан"
    vk_status = f"✅ Привязан (ID: {vk_user_id})" if vk_user_id else "⬇️ Нажмите кнопку «Привязать VK»"
    return (
        f"Никнейм: {nickname}\n"
        f"Telegram: {tg_status}\n"
        f"VK: {vk_status}"
    )


async def get_events_menu_payload(app_user_id: int) -> dict:
    profile = await get_user_profile_by_app_user(app_user_id)
    if not profile or not profile[0]:
        return {
            "has_profile": False,
            "nickname": None,
            "registrations": [],
            "event_counts": {},
            "events": [],
        }

    registrations = await check_user_registration_by_app_user(app_user_id)
    event_counts = await get_all_event_counts()
    events = await get_all_events()
    return {
        "has_profile": True,
        "nickname": profile[0],
        "registrations": registrations,
        "event_counts": event_counts,
        "events": events,
    }


def _build_registered_line(total: int, max_people: int, *, html_mode: bool) -> str:
    limit_text = str(max_people) if max_people and max_people > 0 else "не указано"
    if html_mode:
        return f"<b>Зарегистрировано: {total} из {limit_text}</b>"
    return f"Зарегистрировано: {total} из {limit_text}"


def _get_registered_total(participants: list) -> int:
    return sum((guests or 0) + 1 for _, _, _, guests in participants)


def _build_event_text(
    event: tuple,
    participants: list,
    app_user_id: int,
    *,
    html_mode: bool,
) -> str:
    _, event_name, event_date, event_time, event_address, max_people = event
    total = _get_registered_total(participants)

    if html_mode:
        safe_name = escape(event_name)
        safe_address = escape(event_address) if event_address else ""
        lines = [f"<b>{safe_name}</b>" + (f". {safe_address}" if safe_address else "")]
        lines.append(f"Дата: {escape(event_date)}")
        lines.append(f"Время: {escape(event_time)}")
        lines.append(_build_registered_line(total, max_people, html_mode=True))
        lines.append("")
        if participants:
            lines.append("<b>Список участников:</b>")
            for i, (participant_user_id, nickname, _, guests) in enumerate(participants, 1):
                safe_nickname = escape(nickname or "Без ника")
                is_me = " (вы)" if participant_user_id == app_user_id else ""
                if guests > 0:
                    lines.append(f"{i}. {safe_nickname} +{guests}{is_me}")
                else:
                    lines.append(f"{i}. {safe_nickname}{is_me}")
        else:
            lines.append("Пока никого нет. Будьте первым!")
        return "\n".join(lines)

    lines = [event_name]
    if event_address:
        lines.append(event_address)
    lines.append(f"Дата: {event_date}")
    lines.append(f"Время: {event_time}")
    lines.append(_build_registered_line(total, max_people, html_mode=False))
    lines.append("")
    if participants:
        lines.append("Список участников:")
        for i, (participant_user_id, nickname, _, guests) in enumerate(participants, 1):
            safe_nickname = nickname or "Без ника"
            is_me = " (вы)" if participant_user_id == app_user_id else ""
            if guests > 0:
                lines.append(f"{i}. {safe_nickname} +{guests}{is_me}")
            else:
                lines.append(f"{i}. {safe_nickname}{is_me}")
    else:
        lines.append("Пока никого нет. Будьте первым!")
    return "\n".join(lines)


async def get_event_view(app_user_id: int, event_id: int) -> Optional[EventView]:
    event = await get_event_by_id(event_id)
    if not event:
        return None

    registered = bool(await check_user_registration_by_app_user(app_user_id, event_id))
    participants = await get_event_participants(event_id)
    _, event_name, event_date, event_time, event_address, max_people = event
    total_registered = _get_registered_total(participants)
    return EventView(
        event_id=event_id,
        name=event_name,
        date=event_date,
        time=event_time,
        address=event_address or "",
        max_people=max_people,
        total_registered=total_registered,
        registered=registered,
        participants=participants,
        text_html=_build_event_text(event, participants, app_user_id, html_mode=True),
        text_plain=_build_event_text(event, participants, app_user_id, html_mode=False),
    )


async def build_events_list_text(app_user_id: int) -> str:
    payload = await get_events_menu_payload(app_user_id)
    if not payload["has_profile"]:
        return "Сначала настройте профиль: напишите ник (2-20 символов)."

    events = payload["events"]
    if not events:
        return "Сейчас нет активных мероприятий."

    lines = ["📋 Мероприятия:"]
    for event_id, _, event_date, event_time, _ in events:
        status = " ✅" if event_id in payload["registrations"] else ""
        count = payload["event_counts"].get(event_id, 0)
        day_of_week = get_day_of_week(event_date)
        formatted_date = format_event_date(event_date)
        lines.append(
            f"{event_id}. {day_of_week}, {formatted_date} {event_time}{status} 👥 {count}"
        )
    lines.append("\nЧтобы открыть карточку, напишите: мероприятие <ID>")
    return "\n".join(lines)
