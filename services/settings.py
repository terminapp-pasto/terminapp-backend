"""General texts and rules of the app that the admin can change from the panel.

Each setting has a default here; the app_settings table only stores the ones the
admin changed. Values are cached for a few seconds so every request does not hit
the database, and the cache is cleared as soon as the admin saves a change.
"""

import time

from services.database import connect

CACHE_SECONDS = 30
TEXT = "text"
LONG_TEXT = "long_text"
NUMBER = "number"

# key -> (default, kind, label for the panel, minimum, maximum). For texts, min/max are lengths.
SETTINGS = {
    "home_title": ("¿A dónde viajas hoy", TEXT, "Título de la portada", 3, 60),
    "home_highlight": ("desde Pasto", TEXT, "Parte resaltada del título", 0, 40),
    "home_subtitle": (
        "Escríbelo como se lo dirías a una persona. La IA busca las salidas y tú eliges el asiento.",
        LONG_TEXT, "Texto bajo el título", 0, 200,
    ),
    "announcement": ("", LONG_TEXT, "Aviso para todos los viajeros (vacío = sin aviso)", 0, 240),
    "chat_welcome": ("¡Hola! ¿A dónde quieres viajar hoy?", TEXT, "Saludo del chat", 3, 120),
    "terminal_address": ("Carrera 6ª No. 16D-50, barrio Madrigal, Pasto", TEXT, "Dirección de la terminal", 5, 120),
    "terminal_phones": ("(602) 729 0265 · 302 728 8990", TEXT, "Teléfonos de la terminal", 5, 80),
    "terminal_email": ("pqrs@terminalpasto.gov.co", TEXT, "Correo de la terminal", 5, 80),
    "sales_window_days": (60, NUMBER, "Días hacia adelante en que se venden pasajes", 1, 180),
    "max_pending_purchases": (2, NUMBER, "Compras sin pagar que puede tener un viajero a la vez", 1, 10),
    "boarding_advance_minutes": (30, NUMBER, "Minutos antes de la salida para llegar a abordar", 5, 120),
    "ai_extra_instructions": ("", LONG_TEXT, "Instrucciones extra para el chat con IA (vacío = ninguna)", 0, 1000),
}

_cache = {"values": None, "loaded_at": 0.0}


class SettingError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _load():
    values = {key: spec[0] for key, spec in SETTINGS.items()}
    try:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT key, value FROM app_settings;")
            for key, value in cursor.fetchall():
                if key in SETTINGS:
                    values[key] = int(value) if SETTINGS[key][1] == NUMBER else value
    except Exception:  # noqa: BLE001
        pass  # without the table (or the database) the defaults are used
    return values


def all_settings():
    now = time.monotonic()
    if _cache["values"] is None or now - _cache["loaded_at"] > CACHE_SECONDS:
        _cache["values"] = _load()
        _cache["loaded_at"] = now
    return dict(_cache["values"])


def get_setting(key):
    return all_settings()[key]


def clear_cache():
    _cache["values"] = None


def describe_settings():
    """Every setting with its current value and rules, for the admin panel."""
    values = all_settings()
    return [
        {"key": key, "value": values[key], "default": default, "kind": kind, "label": label, "min": low, "max": high}
        for key, (default, kind, label, low, high) in SETTINGS.items()
    ]


def check_value(key, value):
    if key not in SETTINGS:
        raise SettingError("Ese ajuste no existe", 404)
    _, kind, label, low, high = SETTINGS[key]
    if kind == NUMBER:
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise SettingError(f"{label}: debe ser un número entre {low} y {high}")
        return value
    if not isinstance(value, str):
        raise SettingError(f"{label}: debe ser un texto")
    value = value.strip() if kind == TEXT else value.strip().replace("\r\n", "\n")
    if not low <= len(value) <= high:
        raise SettingError(f"{label}: debe tener entre {low} y {high} caracteres")
    return value


def update_settings(changes):
    """Saves several settings at once (all or nothing). Returns the new values."""
    if not changes:
        raise SettingError("No hay nada que cambiar")
    checked = {key: check_value(key, value) for key, value in changes.items()}
    with connect() as connection, connection.cursor() as cursor:
        for key, value in checked.items():
            cursor.execute(
                """INSERT INTO app_settings (key, value) VALUES (%s, %s)
                   ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();""",
                (key, str(value)),
            )
    clear_cache()
    return all_settings()


def public_settings():
    """What the frontend shows (everything except the AI's private instructions)."""
    values = all_settings()
    values.pop("ai_extra_instructions")
    return values
