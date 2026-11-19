"""Authentication utilities: encrypt and verify passwords.

A password is never stored as is: we store a PBKDF2-SHA256 hash with a random
salt that is different for every user. That way, even someone who sees the
database cannot learn the passwords.

The password does not travel as typed either: the browser sends
SHA-256("terminapp|" + email + "|" + password) (see browser_password_hash), so it
is not readable in the browser's network tools. The server then stores the
PBKDF2 hash of that value, so the password is encrypted twice.
"""

import base64
import hashlib
import hmac
import re
import secrets

HASH_ALGORITHM = "pbkdf2_sha256"
HASH_FUNCTION = "sha256"
HASH_ITERATIONS = 600_000
SALT_SIZE_BYTES = 16
FIELD_SEPARATOR = "$"

# What the browser sends instead of the password: 64 hexadecimal characters
BROWSER_HASH_PREFIX = "terminapp"
BROWSER_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def browser_password_hash(email, password):
    """The same value the browser computes before sending a password (src/passwordHash.ts).
    The email works as a salt, so two users with the same password send different values.
    Used for the accounts the server creates itself, like the test accounts."""
    text = f"{BROWSER_HASH_PREFIX}|{email.strip().lower()}|{password}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_browser_password_hash(text):
    return bool(BROWSER_HASH_PATTERN.match(text))


def _encode_base64(raw_bytes):
    return base64.b64encode(raw_bytes).decode("ascii")


def _derive_hash(password, salt, iterations):
    return hashlib.pbkdf2_hmac(HASH_FUNCTION, password.encode("utf-8"), salt, iterations)


def encrypt_password(password):
    """Returns the text stored in users.password_hash:
    "algorithm$iterations$salt$hash"."""
    salt = secrets.token_bytes(SALT_SIZE_BYTES)
    password_hash = _derive_hash(password, salt, HASH_ITERATIONS)
    return FIELD_SEPARATOR.join(
        [HASH_ALGORITHM, str(HASH_ITERATIONS), _encode_base64(salt), _encode_base64(password_hash)]
    )


def verify_password(password, stored_hash):
    """Checks whether the typed password matches the stored hash."""
    try:
        algorithm, iterations, salt, saved_hash = stored_hash.split(FIELD_SEPARATOR)
        if algorithm != HASH_ALGORITHM:
            return False
        new_hash = _derive_hash(password, base64.b64decode(salt), int(iterations))
    except (ValueError, TypeError, AttributeError):
        return False
    # compare_digest takes the same time whether it matches or not, so timing gives no hints
    return hmac.compare_digest(new_hash, base64.b64decode(saved_hash))
