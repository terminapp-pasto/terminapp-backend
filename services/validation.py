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
# A passport may have letters; the other documents are digits only. These are the
# defaults: the real list lives in the document_types table and the admin can change it.
DEFAULT_DOCUMENT_TYPE = "CC"
DOCUMENT_TYPE_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")


def build_document_type(name, min_length, max_length, allows_letters):
    """(name, pattern, rule) of a document type, built from its lengths (never from a
    regular expression typed by someone, so a bad pattern can never slow the server)."""
    characters = "[A-Z0-9]" if allows_letters else r"\d"
    pattern = re.compile(rf"^{characters}{{{min_length},{max_length}}}$")
    what = "letras y números" if allows_letters else "solo números"
    size = f"{min_length}" if min_length == max_length else f"de {min_length} a {max_length}"
    unit = "caracteres" if allows_letters else "dígitos"
    return name, pattern, f"{name}: {what}, {size} {unit}"


DOCUMENT_TYPES = {
    "CC": build_document_type("Cédula de ciudadanía", 5, 10, False),
    "TI": build_document_type("Tarjeta de identidad", 10, 11, False),
    "CE": build_document_type("Cédula de extranjería", 5, 12, False),
    "PA": build_document_type("Pasaporte", 5, 12, True),
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


def is_valid_document_type(document_type, document_types=None):
    return document_type in (document_types or DOCUMENT_TYPES)


def normalize_document(document):
    """Removes spaces, dots and hyphens ("1.085.123-4" -> "10851234") and uppercases passport letters."""
    return re.sub(r"[\s.-]", "", str(document)).upper()


def document_rule(document_type, document_types=None):
    """The message shown when a document does not match its type."""
    return (document_types or DOCUMENT_TYPES)[document_type][2]


def is_valid_document_of_type(document, document_type, document_types=None):
    document_types = document_types or DOCUMENT_TYPES
    return is_valid_document_type(document_type, document_types) and bool(
        document_types[document_type][1].match(document)
    )


def document_type_rule(document_types=None):
    codes = list(document_types or DOCUMENT_TYPES)
    listed = ", ".join(codes[:-1]) + f" o {codes[-1]}" if len(codes) > 1 else codes[0]
    return f"El tipo de documento debe ser {listed}"


# Colombian mobile: 10 digits starting with 3 ("+57" and spaces are removed first)
PHONE_PATTERN = re.compile(r"^3\d{9}$")
PHONE_RULE = "El celular debe tener 10 dígitos y empezar por 3, por ejemplo 3001234567"


def normalize_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) == 12 and digits.startswith("57"):
        digits = digits[2:]
    return digits


def is_valid_phone(phone):
    return bool(PHONE_PATTERN.match(phone))


def is_valid_email(email):
    return len(email) <= EMAIL_MAX_LENGTH and bool(EMAIL_PATTERN.match(email))


def is_valid_password(password):
    return PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH
