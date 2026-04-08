from datetime import datetime


def format_event_date(date_str: str) -> str:
    """Преобразует дату из DD.MM.YYYY в формат 'D месяц' (без года)"""
    try:
        day, month, year = map(int, date_str.split('.'))
        months = [
            'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
            'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
        ]
        return f"{day} {months[month - 1]}"
    except (ValueError, IndexError):
        return date_str


def get_day_of_week(date_str: str) -> str:
    """Возвращает полный день недели для даты в формате DD.MM.YYYY"""
    try:
        day, month, year = map(int, date_str.split('.'))
        date = datetime(year, month, day)
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        return days[date.weekday()]
    except (ValueError, IndexError):
        return ""
