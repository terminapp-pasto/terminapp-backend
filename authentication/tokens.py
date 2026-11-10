"""Tokens de sesión en formato JWT (HS256).

Cuando el usuario inicia sesión recibe un token firmado con TOKEN_SECRET, que
solo conoce el backend. En cada petición protegida el frontend lo envía en el
encabezado "Authorization: Bearer <token>" y el backend revisa la firma y la
fecha de vencimiento.
"""

import base64
import hashlib
import hmac
import json
import time

import config

TOKEN_LIFETIME_SECONDS = 24 * 60 * 60  # el token vale 24 horas
TOKEN_HEADER = {"alg": "HS256", "typ": "JWT"}


class TokenError(Exception):
    """El token falta, está alterado o ya venció."""


def _encode_base64url(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")


def _decode_base64url(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _secret_key():
    if not config.TOKEN_SECRET:
        raise RuntimeError("Falta la variable de entorno TOKEN_SECRET")
    return config.TOKEN_SECRET.encode("utf-8")


def _sign(content):
    signature = hmac.new(_secret_key(), content.encode("ascii"), hashlib.sha256).digest()
    return _encode_base64url(signature)


def create_token(user_id, name):
    header = _encode_base64url(json.dumps(TOKEN_HEADER).encode())
    now = int(time.time())
    claims = {"sub": str(user_id), "name": name, "iat": now, "exp": now + TOKEN_LIFETIME_SECONDS}
    payload = _encode_base64url(json.dumps(claims).encode())
    content = f"{header}.{payload}"
    return f"{content}.{_sign(content)}"


def decode_token(token):
    """Devuelve los datos (claims) del token si es válido; si no, lanza TokenError."""
    try:
        header, payload, signature = token.split(".")
    except ValueError:
        raise TokenError("Token mal formado")

    if not hmac.compare_digest(signature, _sign(f"{header}.{payload}")):
        raise TokenError("La firma del token no es válida")

    try:
        claims = json.loads(_decode_base64url(payload))
    except ValueError:
        raise TokenError("Token mal formado")

    if claims.get("exp", 0) < time.time():
        raise TokenError("La sesión venció, inicia sesión otra vez")
    return claims
