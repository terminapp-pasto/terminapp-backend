"""Orquestador del chat: conecta la conversación, la IA y las herramientas.

En cada vuelta la IA puede responder con texto (y termina) o pedir una
herramienta. Si pide una, el backend la ejecuta, le devuelve el resultado y la
IA vuelve a pensar con ese dato.
"""

from datetime import timedelta

from ai.gemini import generate_content
from ai.tools import SEARCH_TICKETS, TOOL_DECLARATIONS, run_tool
from services.dates import SALES_WINDOW_DAYS, now_in_colombia

MAX_TOOL_ROUNDS = 5
MAX_HISTORY_MESSAGES = 20
UPCOMING_DAYS_SHOWN = 7

USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"
GEMINI_USER_ROLE = "user"
GEMINI_MODEL_ROLE = "model"

FALLBACK_REPLY = "No te entendí bien, ¿me lo repites?"
TOO_MANY_STEPS_REPLY = "La consulta tomó demasiados pasos. ¿Puedes intentarlo con otras palabras?"

SYSTEM_INSTRUCTIONS = """Eres el asistente de TerminAPP, la plataforma de pasajes de la Terminal de Transportes de Pasto (Nariño, Colombia).

Reglas:
- Responde siempre en español, de forma breve y amable.
- El origen de todos los viajes es Pasto.
- Nunca inventes horarios, precios, empresas ni destinos. Para cualquier dato usa las herramientas.
- Si el usuario no dice el destino, pregúntaselo. Si no sabe a dónde puede ir, consulta los destinos disponibles y díselos.
- Nunca menciones las herramientas ni sus nombres: el usuario no las ve. Tú las usas por él.
- Si el resultado trae una "note" de corrección, dilo con naturalidad, por ejemplo: "Entendí Bogotá".
- Si no hay ruta a ese destino, dilo y nombra los destinos disponibles que trae el resultado.
- Si pide lo más barato, ordena por precio. Si no dice nada, ordena por hora.
- Interpreta las horas así: "en la mañana" o "temprano" desde 05:00, "en la tarde" desde 12:00, "en la noche" o "esta noche" desde 18:00.
- Siempre busca para un día concreto (parámetro date, AAAA-MM-DD). Calcula la fecha a partir de HOY (abajo): "mañana" (sin "en la") es el día siguiente, "pasado mañana" dos días después, "el sábado" es el próximo sábado, "en una semana" son 7 días después, "el 15 de noviembre" es esa fecha. Si no dice día, busca para hoy.
- Solo se venden pasajes desde hoy hasta {sales_days} días adelante.
- Si es para hoy y ya no quedan salidas, dilo y ofrece buscar para mañana.
- Al responder menciona el día del viaje, por ejemplo "el sábado 24 de octubre".
- Escribe los precios en pesos colombianos, por ejemplo $61.000.
- La aplicación muestra todas las salidas encontradas en tarjetas debajo de tu mensaje. No repitas la lista completa: en dos o tres frases recomienda la mejor opción según lo que pidió el usuario y menciona cuántas salidas hay.
- Si no hay salidas, dilo y sugiere buscar desde una hora más temprana.
- Tú no haces la compra directamente. Si el usuario quiere comprar, dile que toque el botón "Comprar" en la tarjeta de la salida que prefiera: ahí elige los asientos, escribe los datos de cada pasajero y paga con tarjeta sin salir de la página. Si todavía no has buscado salidas, búscalas primero para que aparezcan las tarjetas.
- Si preguntan algo que no tiene que ver con pasajes de bus, explica con amabilidad que solo ayudas con viajes desde la Terminal de Pasto.

HOY es {today}. Hora actual en Colombia: {current_time}.
Próximos días: {upcoming_days}.
"""

WEEKDAY_NAMES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTH_NAMES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
               "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def format_date_in_spanish(day):
    return (f"{WEEKDAY_NAMES[day.weekday()]} {day.day} de {MONTH_NAMES[day.month - 1]} "
            f"de {day.year} ({day.isoformat()})")


def build_system_instructions(now=None):
    """Las reglas del asistente con la fecha de hoy, para que entienda "el sábado" o "en una semana"."""
    now = now or now_in_colombia()
    today = now.date()
    upcoming_days = "; ".join(
        format_date_in_spanish(today + timedelta(days=n)) for n in range(1, UPCOMING_DAYS_SHOWN + 1)
    )
    return SYSTEM_INSTRUCTIONS.format(
        sales_days=SALES_WINDOW_DAYS,
        today=format_date_in_spanish(today),
        current_time=now.strftime("%H:%M"),
        upcoming_days=upcoming_days,
    )


def to_gemini_contents(messages):
    """Pasa los mensajes del chat ({role, text}) al formato de Gemini."""
    contents = []
    for message in messages[-MAX_HISTORY_MESSAGES:]:
        role = GEMINI_USER_ROLE if message["role"] == USER_ROLE else GEMINI_MODEL_ROLE
        if not contents and role == GEMINI_MODEL_ROLE:
            continue  # la conversación debe empezar con un mensaje del usuario
        if contents and contents[-1]["role"] == role:
            # dos mensajes seguidos del mismo rol (por ejemplo, tras un error) se unen en uno
            contents[-1]["parts"].append({"text": message["text"]})
            continue
        contents.append({"role": role, "parts": [{"text": message["text"]}]})
    return contents


def generate_reply(messages):
    """Recibe el historial del chat y devuelve la respuesta de la IA y las salidas encontradas."""
    contents = to_gemini_contents(messages)
    departures = []

    for _ in range(MAX_TOOL_ROUNDS):
        content = generate_content(contents, build_system_instructions(), TOOL_DECLARATIONS)
        contents.append(content)  # se guarda tal cual, con su thoughtSignature

        parts = content.get("parts", [])
        function_calls = [part["functionCall"] for part in parts if "functionCall" in part]

        if not function_calls:
            text = "".join(part.get("text", "") for part in parts if not part.get("thought")).strip()
            return {"reply": text or FALLBACK_REPLY, "departures": departures}

        function_responses = []
        for call in function_calls:
            name = call.get("name", "")
            result = run_tool(name, call.get("args") or {})
            if name == SEARCH_TICKETS and "departures" in result:
                departures = result["departures"]
            function_response = {"name": name, "response": result}
            if "id" in call:
                function_response["id"] = call["id"]
            function_responses.append({"functionResponse": function_response})
        contents.append({"role": GEMINI_USER_ROLE, "parts": function_responses})

    return {"reply": TOO_MANY_STEPS_REPLY, "departures": departures}
