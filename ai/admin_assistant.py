"""AI assistant of the admin panel: "cámbiame el precio de Cali a 85 mil".

The AI can look things up (routes, companies, occupancy), but it never changes
anything. When the user asks for a change, the AI calls a "propose_" tool: the
backend checks it (prices, permissions, ranges) and returns it as an action
with a clear summary. The panel shows that action with a "Confirmar" button,
and only that button calls the real admin route. So nothing changes without
the person confirming it.
"""

from ai.gemini import generate_content
from ai.orchestrator import FALLBACK_REPLY, GEMINI_USER_ROLE, TOO_MANY_STEPS_REPLY, MAX_TOOL_ROUNDS, to_gemini_contents
from services import admin, settings
from services.dates import InvalidDateError, now_in_colombia, parse_travel_date

MAX_ACTIONS = 5

SYSTEM_INSTRUCTIONS = """You are the assistant of the TerminAPP admin panel, used by the staff of the Pasto bus terminal (Colombia).
The person talking to you is {who}.

Rules:
- Always answer in Spanish (Colombia), briefly. The person may be speaking by voice, so keep answers short and clear.
- Use the tools to look up routes, departures, prices, companies, buses and occupancy. Never invent data.
- You never change anything yourself. When the person asks for a change, call the matching propose_ tool.
  The panel then shows the change with a "Confirmar" button: tell the person to check it and press it.
  Never say that a change is already done.
- Before proposing, look up the routes to get the right ids. If the request is ambiguous (for example two companies go to Cali,
  or the route has departures with different prices and it is unclear which one), ask which one, unless the person said "todas".
- Prices are in Colombian pesos: "85 mil" is 85000, "ciento veinte mil" is 120000. Write prices like $85.000.
- To change the price of every departure of a route, use propose_route_price. For one departure, use propose_departure_price.
- The reservation time (minutes to pay before the seats are released) is between 5 and 30 minutes; seats per purchase between 1 and 10.
- To move a departure to another hour, use propose_departure_time. To change the duration of a route, use propose_route_duration.
- The texts and general rules of the app (home page title and text, notice banner for travellers, chat greeting,
  terminal address, phones and email, days ahead tickets are sold, unpaid purchases per traveller, minutes to arrive
  before boarding, extra instructions for the travellers' chat) are changed with propose_setting. Use list_settings
  to see the keys and current values. Only the terminal admin can change them.
- If a tool answers with an error, explain it in simple words.
- If they ask about something unrelated to running the terminal, say kindly that you only help with the admin panel.

TODAY is {today}. Current time in Colombia: {current_time}.
"""


def _tool(name, description, properties=None, required=None):
    declaration = {"name": name, "description": description}
    if properties:
        declaration["parameters"] = {"type": "object", "properties": properties, "required": required or []}
    return declaration


INTEGER = {"type": "integer"}

TOOL_DECLARATIONS = [
    _tool("list_routes", "Routes from Pasto with their company, departures (id, time, price, bus, on sale or not).",
          {"destination": {"type": "string", "description": "Optional: only routes to this town, for example Cali."}}),
    _tool("list_companies", "Bus companies with their settings: seats per purchase and minutes to pay."),
    _tool("occupancy", "How full each bus is on a day: sold, held and free seats, and revenue.",
          {"date": {"type": "string", "description": "Day in YYYY-MM-DD format. Today if not given."}}),
    _tool("propose_route_price", "Proposes the same new price for every departure of a route.",
          {"route_id": INTEGER, "price": INTEGER}, ["route_id", "price"]),
    _tool("propose_departure_price", "Proposes a new price for one departure.",
          {"departure_id": INTEGER, "price": INTEGER}, ["departure_id", "price"]),
    _tool("propose_departure_on_sale", "Proposes taking a departure off sale (on_sale false) or back on sale (true).",
          {"departure_id": INTEGER, "on_sale": {"type": "boolean"}}, ["departure_id", "on_sale"]),
    _tool("propose_departure_time", "Proposes moving one departure to another hour (HH:MM, 24 hours).",
          {"departure_id": INTEGER, "departure_time": {"type": "string"}}, ["departure_id", "departure_time"]),
    _tool("propose_route_duration", "Proposes a new travel time in minutes for a route.",
          {"route_id": INTEGER, "duration_min": INTEGER}, ["route_id", "duration_min"]),
    _tool("list_settings", "Texts and general rules of the app with their key, current value and limits."),
    _tool("propose_setting", "Proposes a new value for one text or general rule of the app (admin only).",
          {"key": {"type": "string"}, "text_value": {"type": "string", "description": "For texts."},
           "number_value": {"type": "integer", "description": "For numbers."}}, ["key"]),
    _tool("propose_company_settings",
          "Proposes new settings for a company: minutes to pay before the seats are released and/or seats per purchase.",
          {"company_id": INTEGER, "reservation_minutes": INTEGER, "max_seats_per_purchase": INTEGER}, ["company_id"]),
]


def peso(value):
    return f"${value:,}".replace(",", ".")


class AdminTools:
    """Runs the tools for one person, inside what their role allows."""

    def __init__(self, company_scope):
        self.scope = company_scope
        self.actions = []

    def _routes(self):
        return admin.list_routes(self.scope)

    def _find_departure(self, departure_id):
        for route in self._routes():
            for departure in route["departures"]:
                if departure["id"] == departure_id:
                    return route, departure
        raise admin.AdminError("No encontré esa salida", 404)

    def _propose(self, summary, path, body):
        if len(self.actions) >= MAX_ACTIONS:
            raise admin.AdminError(f"Puedo preparar máximo {MAX_ACTIONS} cambios a la vez")
        self.actions.append({"summary": summary, "path": path, "body": body})
        return {"proposal": summary, "status": "waiting for the person to press Confirmar"}

    def list_routes(self, destination=""):
        destination = str(destination or "").strip().lower()
        return {"routes": [
            {"route_id": r["id"], "company": r["company"], "destination": r["destination"],
             "duration_min": r["duration_min"],
             "departures": [{"departure_id": d["id"], "time": d["departure_time"], "price": d["price"],
                             "on_sale": d["active"], "bus": d["plate"]} for d in r["departures"]]}
            for r in self._routes() if not destination or destination in r["destination"].lower()
        ]}

    def list_companies(self):
        return {"companies": admin.list_companies(self.scope)}

    def occupancy(self, date=""):
        try:
            travel_date = parse_travel_date(date)
        except InvalidDateError as error:
            return {"error": str(error)}
        report = admin.occupancy(self.scope, travel_date)
        report["departures"] = [d for d in report["departures"] if d["sold"] or d["held"]] or "no seats sold or held"
        return report

    def propose_route_price(self, route_id, price):
        admin.check_price(price)
        route = next((r for r in self._routes() if r["id"] == route_id), None)
        if route is None:
            raise admin.AdminError("No encontré esa ruta", 404)
        summary = (f"Cambiar a {peso(price)} el precio de las {len(route['departures'])} salidas "
                   f"de {route['company']} a {route['destination']}")
        return self._propose(summary, f"/admin/routes/{route_id}/price", {"price": price})

    def propose_departure_price(self, departure_id, price):
        admin.check_price(price)
        route, departure = self._find_departure(departure_id)
        summary = (f"Cambiar de {peso(departure['price'])} a {peso(price)} la salida de las "
                   f"{departure['departure_time']} de {route['company']} a {route['destination']}")
        return self._propose(summary, f"/admin/departures/{departure_id}", {"price": price})

    def propose_departure_on_sale(self, departure_id, on_sale):
        route, departure = self._find_departure(departure_id)
        verb = "Volver a vender" if on_sale else "Quitar de la venta"
        summary = f"{verb} la salida de las {departure['departure_time']} de {route['company']} a {route['destination']}"
        return self._propose(summary, f"/admin/departures/{departure_id}", {"active": bool(on_sale)})

    def propose_company_settings(self, company_id, reservation_minutes=None, max_seats_per_purchase=None):
        company = next((c for c in admin.list_companies(self.scope) if c["id"] == company_id), None)
        if company is None:
            raise admin.AdminError("No encontré esa empresa", 404)
        changes, body = [], {}
        if reservation_minutes is not None:
            admin.check_reservation_minutes(reservation_minutes)
            changes.append(f"{reservation_minutes} minutos para pagar")
            body["reservation_minutes"] = reservation_minutes
        if max_seats_per_purchase is not None:
            admin.check_max_seats(max_seats_per_purchase)
            changes.append(f"máximo {max_seats_per_purchase} sillas por compra")
            body["max_seats_per_purchase"] = max_seats_per_purchase
        if not body:
            raise admin.AdminError("No dijiste qué cambiar")
        summary = f"Dejar a {company['name']} con " + " y ".join(changes)
        return self._propose(summary, f"/admin/companies/{company_id}/settings", body)

    def propose_departure_time(self, departure_id, departure_time):
        departure_time = admin.check_time(departure_time)
        route, departure = self._find_departure(departure_id)
        summary = (f"Mover la salida de las {departure['departure_time']} de {route['company']} a "
                   f"{route['destination']} para las {departure_time}")
        return self._propose(summary, f"/admin/departures/{departure_id}", {"departure_time": departure_time})

    def propose_route_duration(self, route_id, duration_min):
        admin._check_range(duration_min, admin.MIN_DURATION, admin.MAX_DURATION, "La duración no es válida")
        route = next((r for r in self._routes() if r["id"] == route_id), None)
        if route is None:
            raise admin.AdminError("No encontré esa ruta", 404)
        summary = f"Dejar la ruta de {route['company']} a {route['destination']} en {duration_min} minutos de viaje"
        return self._propose(summary, f"/admin/routes/{route_id}", {"duration_min": duration_min})

    def list_settings(self):
        return {"settings": [
            {"key": item["key"], "label": item["label"], "value": item["value"], "min": item["min"], "max": item["max"],
             "kind": item["kind"]}
            for item in settings.describe_settings()
        ]}

    def propose_setting(self, key, text_value=None, number_value=None):
        if self.scope is not None:
            raise admin.AdminError("Solo el administrador de la terminal puede cambiar los textos y reglas generales", 403)
        if key not in settings.SETTINGS:
            raise admin.AdminError("Ese ajuste no existe")
        value = number_value if settings.SETTINGS[key][1] == settings.NUMBER else (text_value or "")
        try:
            value = settings.check_value(key, value)
        except settings.SettingError as error:
            raise admin.AdminError(error.message)
        label = settings.SETTINGS[key][2]
        shown = f'"{value}"' if isinstance(value, str) else value
        return self._propose(f"Cambiar {label.lower()} a {shown}", "/admin/settings", {key: value})

    def run(self, name, arguments):
        tools = {
            "list_routes": lambda: self.list_routes(arguments.get("destination", "")),
            "list_companies": self.list_companies,
            "occupancy": lambda: self.occupancy(str(arguments.get("date", ""))),
            "propose_route_price": lambda: self.propose_route_price(
                _integer(arguments, "route_id"), _integer(arguments, "price")),
            "propose_departure_price": lambda: self.propose_departure_price(
                _integer(arguments, "departure_id"), _integer(arguments, "price")),
            "propose_departure_on_sale": lambda: self.propose_departure_on_sale(
                _integer(arguments, "departure_id"), bool(arguments.get("on_sale"))),
            "propose_departure_time": lambda: self.propose_departure_time(
                _integer(arguments, "departure_id"), str(arguments.get("departure_time", ""))),
            "propose_route_duration": lambda: self.propose_route_duration(
                _integer(arguments, "route_id"), _integer(arguments, "duration_min")),
            "list_settings": self.list_settings,
            "propose_setting": lambda: self.propose_setting(
                str(arguments.get("key", "")), arguments.get("text_value"),
                _integer(arguments, "number_value", None)),
            "propose_company_settings": lambda: self.propose_company_settings(
                _integer(arguments, "company_id"), _integer(arguments, "reservation_minutes", None),
                _integer(arguments, "max_seats_per_purchase", None)),
        }
        if name not in tools:
            return {"error": f"There is no tool named {name}"}
        try:
            return tools[name]()
        except admin.AdminError as error:
            return {"error": error.message}
        except (TypeError, ValueError):
            return {"error": "Some value is missing or is not a number"}
        except Exception:
            return {"error": "The database could not be queried right now"}


def _integer(arguments, key, default=0):
    value = arguments.get(key, default)
    return None if value is None else int(value)


def build_system_instructions(user, now=None):
    now = now or now_in_colombia()
    who = "the terminal admin (can manage every company)" if user["role"] == "admin" else (
        f"an employee of the company {user['company']} (can only manage that company)"
    )
    return SYSTEM_INSTRUCTIONS.format(who=who, today=now.date().isoformat(), current_time=now.strftime("%H:%M"))


def generate_admin_reply(messages, user, company_scope):
    """Answers the panel conversation. Returns the reply and the actions waiting for confirmation."""
    contents = to_gemini_contents(messages)
    tools = AdminTools(company_scope)
    instructions = build_system_instructions(user)

    for _ in range(MAX_TOOL_ROUNDS):
        content = generate_content(contents, instructions, TOOL_DECLARATIONS)
        contents.append(content)
        parts = content.get("parts", [])
        function_calls = [part["functionCall"] for part in parts if "functionCall" in part]
        if not function_calls:
            text = "".join(part.get("text", "") for part in parts if not part.get("thought")).strip()
            return {"reply": text or FALLBACK_REPLY, "actions": tools.actions}

        responses = []
        for call in function_calls:
            response = {"name": call.get("name", ""), "response": tools.run(call.get("name", ""), call.get("args") or {})}
            if "id" in call:
                response["id"] = call["id"]
            responses.append({"functionResponse": response})
        contents.append({"role": GEMINI_USER_ROLE, "parts": responses})

    return {"reply": TOO_MANY_STEPS_REPLY, "actions": tools.actions}
