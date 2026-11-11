"""Tools the AI can ask the backend to run.

The AI never searches or invents schedules: it only decides which tool to use
and with which data. Each tool calls the search engine, which works with the
graph, the AVL tree and the heap.
"""

from services.data_loader import load_graph
from services.dates import InvalidDateError, parse_travel_date
from services.search import SORT_BY_PRICE, SORT_BY_TIME, search_departures

ORIGIN = "Pasto"
SEARCH_TICKETS = "search_tickets"
LIST_DESTINATIONS = "list_destinations"

# Description of each tool in the format Gemini understands.
TOOL_DECLARATIONS = [
    {
        "name": SEARCH_TICKETS,
        "description": (
            "Searches the bus departures from the Pasto terminal to a destination on one day, "
            "from a given time on, sorted by departure time or by price, with that day's free seats. "
            "Use it whenever the user asks about tickets, schedules or prices."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Destination town, for example Cali, Ipiales or Sandoná.",
                },
                "date": {
                    "type": "string",
                    "description": "Travel day in YYYY-MM-DD format. If the user does not say the day, use today's date.",
                },
                "from_time": {
                    "type": "string",
                    "description": "Earliest departure time in 24-hour HH:MM format. Use 00:00 if the user does not say a time.",
                },
                "sort_by": {
                    "type": "string",
                    "enum": [SORT_BY_TIME, SORT_BY_PRICE],
                    "description": "time to sort by departure time, price to sort from cheapest to most expensive.",
                },
            },
            "required": ["destination"],
        },
    },
    {
        "name": LIST_DESTINATIONS,
        "description": "Returns the towns that buses leave for from the Pasto terminal.",
    },
]


def parse_time_to_minutes(text):
    """Converts "HH:MM" into minutes after midnight; raises ValueError if it cannot."""
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
        return {"error": "The time must use the HH:MM format"}

    if sort_by not in (SORT_BY_TIME, SORT_BY_PRICE):
        sort_by = SORT_BY_TIME

    result = {"date": travel_date.isoformat()}
    departures = search_departures(ORIGIN, destination, start_minutes, sort_by, travel_date)
    if departures is None:
        # it may be a typo: "bodota" -> Bogotá
        closest = load_graph().find_closest(destination)
        if closest is not None and closest.name != ORIGIN:
            departures = search_departures(ORIGIN, closest.name, start_minutes, sort_by, travel_date)
            result["note"] = f'The user wrote "{destination}"; it was understood as {closest.name}.'
    if departures is None:
        return {
            "error": f"There are no routes from {ORIGIN} to {destination}.",
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
    """Runs the tool the AI asked for and returns its result."""
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
        return {"error": f"There is no tool named {name}"}
    except Exception:
        return {"error": "The database could not be queried right now"}
