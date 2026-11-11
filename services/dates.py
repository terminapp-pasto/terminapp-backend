"""Colombian dates and times, and the rules for which days tickets are sold."""

from datetime import date, datetime, timedelta, timezone

COLOMBIA_TIMEZONE = timezone(timedelta(hours=-5))  # Colombia has no daylight saving time
SALES_WINDOW_DAYS = 60   # tickets are sold up to 60 days ahead


class InvalidDateError(Exception):
    """The date has the wrong format or is outside the sales window."""


def now_in_colombia():
    return datetime.now(COLOMBIA_TIMEZONE)


def today_in_colombia():
    return now_in_colombia().date()


def parse_date(text):
    """Reads a YYYY-MM-DD date."""
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        raise InvalidDateError("La fecha debe tener el formato AAAA-MM-DD")


def parse_travel_date(text):
    """Reads a YYYY-MM-DD date (empty = today) and checks that tickets are sold for that day."""
    today = today_in_colombia()
    travel_date = today if not text else parse_date(text)
    if travel_date < today:
        raise InvalidDateError("Esa fecha ya pasó. Elige hoy o un día futuro")
    if travel_date > today + timedelta(days=SALES_WINDOW_DAYS):
        raise InvalidDateError(f"Solo se venden pasajes hasta {SALES_WINDOW_DAYS} días adelante")
    return travel_date
