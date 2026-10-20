"""Orquestador del chat: conecta la conversación, la IA y las herramientas.

En cada vuelta la IA puede responder con texto (y termina) o pedir una
herramienta. Si pide una, el backend la ejecuta, le devuelve el resultado y la
IA vuelve a pensar con ese dato.
"""

from ia.gemini import generar
from ia.herramientas import DECLARACIONES, ejecutar

MAX_VUELTAS = 5
MAX_MENSAJES = 20

INSTRUCCIONES = """Eres el asistente de TerminAPP, la plataforma de pasajes de la Terminal de Transportes de Pasto (Nariño, Colombia).

Reglas:
- Responde siempre en español, de forma breve y amable.
- El origen de todos los viajes es Pasto.
- Nunca inventes horarios, precios, empresas ni destinos. Para cualquier dato usa las herramientas.
- Si el usuario no dice el destino, pregúntaselo. Si no sabe a dónde puede ir, usa listar_destinos.
- Si pide lo más barato, ordena por precio. Si no dice nada, ordena por hora.
- Interpreta las horas así: "en la mañana" desde 05:00, "en la tarde" desde 12:00, "en la noche" o "esta noche" desde 18:00.
- Escribe los precios en pesos colombianos, por ejemplo $61.000.
- Si no hay salidas, dilo y sugiere buscar desde una hora más temprana.
- Todavía no puedes vender pasajes. Si el usuario quiere comprar, dile que la compra en línea estará disponible muy pronto y que mientras tanto puede comprar en la taquilla de la empresa.
- Si preguntan algo que no tiene que ver con pasajes de bus, explica con amabilidad que solo ayudas con viajes desde la Terminal de Pasto.
"""


def _convertir(mensajes):
    """Pasa los mensajes del chat al formato de Gemini."""
    contenidos = []
    for mensaje in mensajes[-MAX_MENSAJES:]:
        rol = "user" if mensaje["rol"] == "usuario" else "model"
        if not contenidos and rol == "model":
            continue  # la conversación debe empezar con un mensaje del usuario
        contenidos.append({"role": rol, "parts": [{"text": mensaje["texto"]}]})
    return contenidos


def responder(mensajes):
    """Recibe el historial del chat y devuelve la respuesta de la IA y las salidas encontradas."""
    contenidos = _convertir(mensajes)
    salidas = []

    for _ in range(MAX_VUELTAS):
        contenido = generar(contenidos, INSTRUCCIONES, DECLARACIONES)
        contenidos.append(contenido)

        partes = contenido.get("parts", [])
        llamadas = [parte["functionCall"] for parte in partes if "functionCall" in parte]

        if not llamadas:
            texto = "".join(
                parte.get("text", "") for parte in partes if not parte.get("thought")
            ).strip()
            return {"respuesta": texto or "No te entendí bien, ¿me lo repites?", "salidas": salidas}

        respuestas = []
        for llamada in llamadas:
            resultado = ejecutar(llamada.get("name", ""), llamada.get("args") or {})
            if llamada.get("name") == "buscar_pasajes" and "salidas" in resultado:
                salidas = resultado["salidas"]
            respuesta = {"name": llamada.get("name", ""), "response": resultado}
            if "id" in llamada:
                respuesta["id"] = llamada["id"]
            respuestas.append({"functionResponse": respuesta})
        contenidos.append({"role": "user", "parts": respuestas})

    return {
        "respuesta": "La consulta tomó demasiados pasos. ¿Puedes intentarlo con otras palabras?",
        "salidas": salidas,
    }
