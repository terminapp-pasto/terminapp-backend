"""Utilidades de autenticación: cifrar y verificar contraseñas.

La contraseña nunca se guarda tal cual: se guarda un hash PBKDF2-SHA256 con una
sal (salt) aleatoria distinta para cada usuario. Así, aunque alguien vea la
base de datos, no puede saber las contraseñas.
"""

import base64
import hashlib
import hmac
import secrets

HASH_ALGORITHM = "pbkdf2_sha256"
HASH_FUNCTION = "sha256"
HASH_ITERATIONS = 600_000
SALT_SIZE_BYTES = 16
FIELD_SEPARATOR = "$"


def _encode_base64(raw_bytes):
    return base64.b64encode(raw_bytes).decode("ascii")


def _derive_hash(password, salt, iterations):
    return hashlib.pbkdf2_hmac(HASH_FUNCTION, password.encode("utf-8"), salt, iterations)


def encrypt_password(password):
    """Devuelve el texto que se guarda en users.password_hash:
    "algoritmo$iteraciones$salt$hash"."""
    salt = secrets.token_bytes(SALT_SIZE_BYTES)
    password_hash = _derive_hash(password, salt, HASH_ITERATIONS)
    return FIELD_SEPARATOR.join(
        [HASH_ALGORITHM, str(HASH_ITERATIONS), _encode_base64(salt), _encode_base64(password_hash)]
    )


def verify_password(password, stored_hash):
    """Comprueba si la contraseña escrita coincide con el hash guardado."""
    try:
        algorithm, iterations, salt, saved_hash = stored_hash.split(FIELD_SEPARATOR)
        if algorithm != HASH_ALGORITHM:
            return False
        new_hash = _derive_hash(password, base64.b64decode(salt), int(iterations))
    except (ValueError, TypeError, AttributeError):
        return False
    # compare_digest tarda lo mismo acierte o no, para no dar pistas por el tiempo
    return hmac.compare_digest(new_hash, base64.b64decode(saved_hash))
