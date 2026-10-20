"""Conexión con la API de Gemini.

Es el único archivo que sabe hablar con el proveedor de IA. Si algún día se
cambia de proveedor, solo se reemplaza este archivo.
"""

import json
import os
import urllib.error
import urllib.request

URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
MODELO_POR_DEFECTO = "gemini-3.5-flash-lite"


class ErrorIA(Exception):
    """La IA no pudo responder: falta la clave, no hay conexión o el servicio dio error."""


def generar(contenidos, instrucciones, herramientas):
    """Envía la conversación a Gemini y devuelve el mensaje que responde el modelo."""
    clave = os.getenv("GEMINI_API_KEY")
    if not clave:
        raise ErrorIA("Falta la variable de entorno GEMINI_API_KEY")

    modelo = os.getenv("GEMINI_MODEL", MODELO_POR_DEFECTO)
    cuerpo = {
        "systemInstruction": {"parts": [{"text": instrucciones}]},
        "contents": contenidos,
        "tools": [{"functionDeclarations": herramientas}],
    }
    peticion = urllib.request.Request(
        URL_GEMINI.format(modelo=modelo),
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": clave},
        method="POST",
    )

    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", errors="replace")[:500]
        raise ErrorIA(f"Gemini respondió con el código {error.code}: {detalle}") from error
    except urllib.error.URLError as error:
        raise ErrorIA(f"No se pudo conectar con Gemini: {error.reason}") from error

    candidatos = datos.get("candidates") or []
    if not candidatos or "content" not in candidatos[0]:
        raise ErrorIA("Gemini no devolvió ninguna respuesta")
    return candidatos[0]["content"]
