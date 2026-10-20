"""Tokens de sesión en formato JWT (HS256).

Cuando el usuario inicia sesión recibe un token firmado con CLAVE_TOKENS, que
solo conoce el backend. En cada petición protegida el frontend lo envía en el
encabezado "Authorization: Bearer <token>" y el backend revisa la firma y la
fecha de vencimiento.
"""

import base64
import hashlib
import hmac
import json
import os
import time

DURACION_SEGUNDOS = 24 * 60 * 60  # el token vale 24 horas


class ErrorToken(Exception):
    """El token falta, está alterado o ya venció."""


def _codificar(datos):
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode("ascii")


def _decodificar(texto):
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _clave():
    clave = os.getenv("CLAVE_TOKENS")
    if not clave:
        raise RuntimeError("Falta la variable de entorno CLAVE_TOKENS")
    return clave.encode("utf-8")


def _firmar(contenido):
    return _codificar(hmac.new(_clave(), contenido.encode("ascii"), hashlib.sha256).digest())


def crear_token(usuario_id, nombre):
    encabezado = _codificar(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    ahora = int(time.time())
    datos = {"sub": str(usuario_id), "nombre": nombre, "iat": ahora, "exp": ahora + DURACION_SEGUNDOS}
    cuerpo = _codificar(json.dumps(datos).encode())
    contenido = f"{encabezado}.{cuerpo}"
    return f"{contenido}.{_firmar(contenido)}"


def leer_token(token):
    """Devuelve los datos del token si es válido; si no, lanza ErrorToken."""
    try:
        encabezado, cuerpo, firma = token.split(".")
    except ValueError:
        raise ErrorToken("Token mal formado")

    if not hmac.compare_digest(firma, _firmar(f"{encabezado}.{cuerpo}")):
        raise ErrorToken("La firma del token no es válida")

    try:
        datos = json.loads(_decodificar(cuerpo))
    except ValueError:
        raise ErrorToken("Token mal formado")

    if datos.get("exp", 0) < time.time():
        raise ErrorToken("La sesión venció, inicia sesión otra vez")
    return datos
