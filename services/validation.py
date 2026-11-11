"""Form validation rules, using regular expressions.

The same rules are checked in the frontend (to warn early) and here in the
backend (because anyone can call the API without going through the frontend).
The maximum lengths match the database columns, so a huge text pasted into a
field never reaches the database.
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

# Letters (with accents and ñ), spaces, apostrophe, dot and hyphen: "María José", "O'Neil", "Ana-Lucía".
# Must start with a letter; digits and symbols are not allowed.
NAME_PATTERN = re.compile(
    rf"^(?=.{{{NAME_MIN_LENGTH},{NAME_MAX_LENGTH}}}$)[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]*$"
)
# Digits only, 5 to 12 (national ID, identity card or numeric passport).
DOCUMENT_PATTERN = re.compile(rf"^\d{{{DOCUMENT_MIN_LENGTH},{DOCUMENT_MAX_LENGTH}}}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

NAME_RULE = f"El nombre solo puede tener letras y espacios, de {NAME_MIN_LENGTH} a {NAME_MAX_LENGTH} caracteres"
DOCUMENT_RULE = f"El documento solo puede tener números, de {DOCUMENT_MIN_LENGTH} a {DOCUMENT_MAX_LENGTH} dígitos"
EMAIL_RULE = f"El correo no es válido (máximo {EMAIL_MAX_LENGTH} caracteres)"
PASSWORD_RULE = f"La contraseña debe tener entre {PASSWORD_MIN_LENGTH} y {PASSWORD_MAX_LENGTH} caracteres"


def normalize_spaces(text):
    """Trims spaces at both ends and leaves a single space between words."""
    return " ".join(str(text).split())


def is_valid_name(name):
    return bool(NAME_PATTERN.match(name))


def is_valid_document(document):
    return bool(DOCUMENT_PATTERN.match(document))


def is_valid_email(email):
    return len(email) <= EMAIL_MAX_LENGTH and bool(EMAIL_PATTERN.match(email))


def is_valid_password(password):
    return PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH
