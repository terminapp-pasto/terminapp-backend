"""Herramientas que la IA puede pedirle al backend.

La IA no busca ni inventa horarios: solo decide qué herramienta usar y con qué
datos. Cada herramienta llama al motor de búsqueda, que trabaja con el grafo,
el árbol AVL y el heap.
"""

from services.data_loader import load_graph
from services.dates import InvalidDateError, parse_travel_date
from services.search import SORT_BY_PRICE, SORT_BY_TIME, search_departures

ORIGIN = "Pasto"
SEARCH_TICKETS = "search_tickets"
LIST_DESTINATIONS = "list_destinations"

# Descripción de cada herramienta en el formato que entiende Gemini.
TOOL_DECLARATIONS = [
    {
        "name": SEARCH_TICKETS,
        "description": (
            "Busca las salidas de bus desde la Terminal de Pasto hacia un destino en un día, "
            "a partir de una hora, ordenadas por hora de salida o por precio, con los cupos libres de ese día. "
            "Úsala siempre que el usuario pregunte por pasajes, horarios o precios."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Municipio de destino, por ejemplo Cali, Ipiales o Sandoná.",
                },
                "date": {
                    "type": "string",
                    "description": "Día del viaje en formato AAAA-MM-DD. Si el usuario no dice el día, usa la fecha de hoy.",
                },
                "from_time": {
                    "type": "string",
                    "description": "Hora mínima de salida en formato HH:MM de 24 horas. Usa 00:00 si el usuario no dice una hora.",
                },
                "sort_by": {
                    "type": "string",
                    "enum": [SORT_BY_TIME, SORT_BY_PRICE],
                    "description": "time para ordenar por hora de salida, price para ordenar del más barato al más caro.",
                },
            },
            "required": ["destination"],
        },
    },
    {
        "name": LIST_DESTINATIONS,
        "description": "Devuelve los municipios a los que salen buses desde la Terminal de Pasto.",
    },
]


def parse_time_to_minutes(text):
    """Convierte "HH:MM" en minutos desde la medianoche; lanza ValueError si no se puede."""
    hours, minutes = str(text).split(":")
    hours, minutes = int(hours), int(minutes)
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise ValueError("Hora fuera de rango")
    return hours * 60 + minutes


def search_tickets(destination, from_time="00:00", sort_by=SORT_BY_TIME, date=""):
    try:
        travel_date = parse_travel_date(date)
    except InvalidDateError as error:
        return {"error": str(error)}
    try:
        start_minutes = parse_time_to_minutes(from_time)
    except ValueError:
        return {"error": "La hora debe tener el formato HH:MM"}

    if sort_by not in (SORT_BY_TIME, SORT_BY_PRICE):
        sort_by = SORT_BY_TIME

    result = {"date": travel_date.isoformat()}
    departures = search_departures(ORIGIN, destination, start_minutes, sort_by, travel_date)
    if departures is None:
        # puede ser un error de escritura: "bodota" -> Bogotá
        closest = load_graph().find_closest(destination)
        if closest is not None and closest.name != ORIGIN:
            departures = search_departures(ORIGIN, closest.name, start_minutes, sort_by, travel_date)
            result["note"] = f'El usuario escribió "{destination}"; se entendió como {closest.name}.'
    if departures is None:
        return {
            "error": f"No hay rutas desde {ORIGIN} hacia {destination}.",
            "available_destinations": list_destinations()["destinations"],
        }
    result.update({"count": len(departures), "departures": departures})
    return result


def list_destinations():
    graph = load_graph()
    vertex = graph.find_vertex(ORIGIN)
    destinations = []
    edge = vertex.first_edge if vertex is not None else None
    while edge is not None:
        if edge.destination not in destinations:
            destinations.append(edge.destination)
        edge = edge.next
    return {"origin": ORIGIN, "destinations": destinations}


def run_tool(name, arguments):
    """Ejecuta la herramienta que pidió la IA y devuelve su resultado."""
    try:
        if name == SEARCH_TICKETS:
            return search_tickets(
                destination=str(arguments.get("destination", "")),
                from_time=str(arguments.get("from_time", "00:00")),
                sort_by=str(arguments.get("sort_by", SORT_BY_TIME)),
                date=str(arguments.get("date", "")),
            )
        if name == LIST_DESTINATIONS:
            return list_destinations()
        return {"error": f"No existe la herramienta {name}"}
    except Exception:
        return {"error": "No se pudo consultar la base de datos en este momento"}
