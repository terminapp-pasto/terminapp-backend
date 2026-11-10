"""Conexión con la API de Gemini.

Es el único archivo que sabe hablar con el proveedor de IA. Si algún día se
cambia de proveedor, solo se reemplaza este archivo.
"""

import json
import urllib.error
import urllib.request

import config

REQUEST_TIMEOUT_SECONDS = 30
ERROR_DETAIL_MAX_LENGTH = 500


class AIError(Exception):
    """La IA no pudo responder: falta la clave, no hay conexión o el servicio dio error."""


def generate_content(contents, system_instructions, tool_declarations):
    """Envía la conversación a Gemini y devuelve el mensaje con que responde el modelo."""
    if not config.GEMINI_API_KEY:
        raise AIError("Falta la variable de entorno GEMINI_API_KEY")

    body = {
        "systemInstruction": {"parts": [{"text": system_instructions}]},
        "contents": contents,
        "tools": [{"functionDeclarations": tool_declarations}],
    }
    request = urllib.request.Request(
        config.GEMINI_API_URL.format(model=config.GEMINI_MODEL),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": config.GEMINI_API_KEY},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:ERROR_DETAIL_MAX_LENGTH]
        raise AIError(f"Gemini respondió con el código {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise AIError(f"No se pudo conectar con Gemini: {error.reason}") from error

    candidates = data.get("candidates") or []
    if not candidates or "content" not in candidates[0]:
        raise AIError("Gemini no devolvió ninguna respuesta")
    return candidates[0]["content"]
