"""Chat orchestrator: connects the conversation, the AI and the tools.

On each round the AI either answers with text (and we are done) or asks for a
tool. If it asks for one, the backend runs it, sends back the result, and the
AI thinks again with that data.
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

SYSTEM_INSTRUCTIONS = """You are the assistant of TerminAPP, the ticket platform of the Pasto bus terminal (Terminal de Transportes de Pasto, Nariño, Colombia).

Rules:
- Always answer in Spanish (Colombia), briefly and kindly, whatever language these rules are written in.
- Every trip starts in Pasto.
- Never invent schedules, prices, companies or destinations. Use the tools for any data.
- If the user does not say the destination, ask for it. If they do not know where they can go, look up the available destinations and tell them.
- Never mention the tools or their names: the user cannot see them. You use them on the user's behalf.
- If the result includes a correction "note", say it naturally, for example: "Entendí Bogotá".
- If there is no route to that destination, say so and name the available destinations included in the result.
- If they ask for the cheapest option, sort by price. Otherwise sort by time.
- Read times like this: "en la mañana" or "temprano" from 05:00, "en la tarde" from 12:00, "en la noche" or "esta noche" from 18:00.
- Always search for one specific day (date parameter, YYYY-MM-DD). Work the date out from TODAY (below): "mañana" (without "en la") is the next day, "pasado mañana" is two days later, "el sábado" is the coming Saturday, "en una semana" is 7 days later, "el 15 de noviembre" is that date. If no day is given, search for today.
- Tickets are only sold from today up to {sales_days} days ahead.
- If the trip is for today and no departures are left, say so and offer to search for tomorrow.
- When answering, mention the travel day in Spanish, for example "el sábado 24 de octubre".
- Write prices in Colombian pesos, for example $61.000.
- The app shows every departure found as cards below your message. Do not repeat the full list: in two or three sentences recommend the best option for what the user asked and say how many departures there are.
- If there are no departures, say so and suggest searching from an earlier time.
- You do not make the purchase yourself. If the user wants to buy, tell them to tap the "Comprar" button on the card of the departure they prefer: there they choose the seats, enter each passenger's details and pay by card without leaving the page. If you have not searched yet, search first so the cards appear.
- If they ask about something unrelated to bus tickets, kindly explain that you only help with trips from the Pasto bus terminal.

TODAY is {today}. Current time in Colombia: {current_time}.
Next days: {upcoming_days}.
(Dates are written in Spanish, the same way the user writes them.)
"""

WEEKDAY_NAMES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTH_NAMES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
               "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def format_date_in_spanish(day):
    return (f"{WEEKDAY_NAMES[day.weekday()]} {day.day} de {MONTH_NAMES[day.month - 1]} "
            f"de {day.year} ({day.isoformat()})")


def build_system_instructions(now=None):
    """The assistant rules with today's date, so it understands "el sábado" or "en una semana"."""
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
    """Converts the chat messages ({role, text}) to the Gemini format."""
    contents = []
    for message in messages[-MAX_HISTORY_MESSAGES:]:
        role = GEMINI_USER_ROLE if message["role"] == USER_ROLE else GEMINI_MODEL_ROLE
        if not contents and role == GEMINI_MODEL_ROLE:
            continue  # the conversation must start with a user message
        if contents and contents[-1]["role"] == role:
            # two messages in a row from the same role (for example after an error) are merged
            contents[-1]["parts"].append({"text": message["text"]})
            continue
        contents.append({"role": role, "parts": [{"text": message["text"]}]})
    return contents


def generate_reply(messages):
    """Receives the chat history and returns the AI reply and the departures found."""
    contents = to_gemini_contents(messages)
    departures = []

    for _ in range(MAX_TOOL_ROUNDS):
        content = generate_content(contents, build_system_instructions(), TOOL_DECLARATIONS)
        contents.append(content)  # kept as is, together with its thoughtSignature

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
