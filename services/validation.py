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

# Colombian identity documents accepted for bus travel: code -> (name, pattern, rule).
# A passport may have letters; the other documents are digits only.
DEFAULT_DOCUMENT_TYPE = "CC"
DOCUMENT_TYPES = {
    "CC": ("Cédula de ciudadanía", re.compile(r"^\d{5,10}$"), "La cédula tiene solo números, de 5 a 10 dígitos"),
    "TI": ("Tarjeta de identidad", re.compile(r"^\d{10,11}$"), "La tarjeta de identidad tiene 10 u 11 dígitos"),
    "CE": ("Cédula de extranjería", re.compile(r"^\d{5,12}$"), "La cédula de extranjería tiene de 5 a 12 dígitos"),
    "PA": ("Pasaporte", re.compile(r"^[A-Z0-9]{5,12}$"), "El pasaporte tiene letras y números, de 5 a 12 caracteres"),
}
DOCUMENT_TYPE_RULE = "El tipo de documento debe ser CC, TI, CE o PA"
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


def is_valid_document_type(document_type):
    return document_type in DOCUMENT_TYPES


def normalize_document(document):
    """Removes spaces, dots and hyphens ("1.085.123-4" -> "10851234") and uppercases passport letters."""
    return re.sub(r"[\s.-]", "", str(document)).upper()


def document_rule(document_type):
    """The message shown when a document does not match its type."""
    return DOCUMENT_TYPES[document_type][2]


def is_valid_document_of_type(document, document_type):
    return is_valid_document_type(document_type) and bool(DOCUMENT_TYPES[document_type][1].match(document))


def is_valid_email(email):
    return len(email) <= EMAIL_MAX_LENGTH and bool(EMAIL_PATTERN.match(email))


def is_valid_password(password):
    return PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH
