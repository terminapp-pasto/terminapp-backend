"""Reglas de validación de los formularios, con expresiones regulares.

Las mismas reglas se revisan en el frontend (para avisar rápido) y aquí en el
backend (porque cualquiera puede llamar a la API sin pasar por el frontend).
Los largos máximos coinciden con los de la base de datos, para que un texto
gigante pegado en un campo nunca llegue a ella.
"""

import re

NAME_MIN_LENGTH = 3
NAME_MAX_LENGTH = 50
DOCUMENT_MIN_LENGTH = 5
DOCUMENT_MAX_LENGTH = 12
EMAIL_MAX_LENGTH = 100
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 72
CHAT_MESSAGE_MAX_LENGTH = 1000
CHAT_MAX_MESSAGES = 40

# Letras (con tildes y ñ), espacios, apóstrofo, punto y guion: "María José", "O'Neil", "Ana-Lucía".
# Debe empezar con una letra y no acepta números ni símbolos.
NAME_PATTERN = re.compile(
    rf"^(?=.{{{NAME_MIN_LENGTH},{NAME_MAX_LENGTH}}}$)[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]*$"
)
# Solo dígitos, de 5 a 12 (cédula, tarjeta de identidad o pasaporte numérico).
DOCUMENT_PATTERN = re.compile(rf"^\d{{{DOCUMENT_MIN_LENGTH},{DOCUMENT_MAX_LENGTH}}}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

NAME_RULE = f"El nombre solo puede tener letras y espacios, de {NAME_MIN_LENGTH} a {NAME_MAX_LENGTH} caracteres"
DOCUMENT_RULE = f"El documento solo puede tener números, de {DOCUMENT_MIN_LENGTH} a {DOCUMENT_MAX_LENGTH} dígitos"
EMAIL_RULE = f"El correo no es válido (máximo {EMAIL_MAX_LENGTH} caracteres)"
PASSWORD_RULE = f"La contraseña debe tener entre {PASSWORD_MIN_LENGTH} y {PASSWORD_MAX_LENGTH} caracteres"


def normalize_spaces(text):
    """Quita espacios al inicio y al final, y deja uno solo entre palabras."""
    return " ".join(str(text).split())


def is_valid_name(name):
    return bool(NAME_PATTERN.match(name))


def is_valid_document(document):
    return bool(DOCUMENT_PATTERN.match(document))


def is_valid_email(email):
    return len(email) <= EMAIL_MAX_LENGTH and bool(EMAIL_PATTERN.match(email))


def is_valid_password(password):
    return PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH
