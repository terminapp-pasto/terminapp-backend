"""Fechas y horas de Colombia, y reglas de qué días se venden pasajes."""

from datetime import date, datetime, timedelta, timezone

COLOMBIA_TIMEZONE = timezone(timedelta(hours=-5))  # Colombia no tiene horario de verano
SALES_WINDOW_DAYS = 60   # se venden pasajes hasta 60 días adelante


class InvalidDateError(Exception):
    """La fecha no tiene el formato correcto o no está en la ventana de venta."""


def now_in_colombia():
    return datetime.now(COLOMBIA_TIMEZONE)


def today_in_colombia():
    return now_in_colombia().date()


def parse_date(text):
    """Lee una fecha AAAA-MM-DD."""
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        raise InvalidDateError("La fecha debe tener el formato AAAA-MM-DD")


def parse_travel_date(text):
    """Lee una fecha AAAA-MM-DD (vacía = hoy) y revisa que se vendan pasajes para ese día."""
    today = today_in_colombia()
    travel_date = today if not text else parse_date(text)
    if travel_date < today:
        raise InvalidDateError("Esa fecha ya pasó. Elige hoy o un día futuro")
    if travel_date > today + timedelta(days=SALES_WINDOW_DAYS):
        raise InvalidDateError(f"Solo se venden pasajes hasta {SALES_WINDOW_DAYS} días adelante")
    return travel_date
