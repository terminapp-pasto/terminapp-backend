"""Cifrado de contraseñas.

La contraseña nunca se guarda tal cual: se guarda un hash PBKDF2-SHA256 con una
sal aleatoria distinta para cada usuario. Así, aunque alguien vea la base de
datos, no puede saber las contraseñas.
"""

import base64
import hashlib
import hmac
import secrets

ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 600_000


def _a_texto(datos):
    return base64.b64encode(datos).decode("ascii")


def cifrar_contrasena(contrasena):
    """Devuelve el texto que se guarda en usuarios.password_hash."""
    sal = secrets.token_bytes(16)
    hash_ = hashlib.pbkdf2_hmac("sha256", contrasena.encode("utf-8"), sal, ITERACIONES)
    return f"{ALGORITMO}${ITERACIONES}${_a_texto(sal)}${_a_texto(hash_)}"


def verificar_contrasena(contrasena, guardado):
    """Comprueba si la contraseña escrita coincide con el hash guardado."""
    try:
        algoritmo, iteraciones, sal, hash_guardado = guardado.split("$")
        if algoritmo != ALGORITMO:
            return False
        hash_nuevo = hashlib.pbkdf2_hmac(
            "sha256", contrasena.encode("utf-8"), base64.b64decode(sal), int(iteraciones)
        )
    except (ValueError, TypeError):
        return False
    # compare_digest tarda lo mismo acierte o no, para no dar pistas por el tiempo
    return hmac.compare_digest(hash_nuevo, base64.b64decode(hash_guardado))
