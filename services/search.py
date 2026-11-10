"""Motor de búsqueda de salidas: grafo → árbol AVL → montículo de mínimos."""

from services.data_loader import load_graph, load_schedules
from services.dates import now_in_colombia, today_in_colombia
from services.purchases import count_taken_seats_by_schedule
from structs.avl_tree import minutes_to_text
from structs.min_heap import MinHeap

SORT_BY_TIME = "time"
SORT_BY_PRICE = "price"
MINUTES_PER_DAY = 1440


def search_departures(origin, destination, start_minutes=0, sort_by=SORT_BY_TIME, travel_date=None):
    """Salidas de un día (hoy si no se dice) desde una hora, con los cupos libres reales.
    Devuelve None si el origen o el destino no existen."""
    travel_date = travel_date or today_in_colombia()
    if travel_date == today_in_colombia():
        now = now_in_colombia()
        start_minutes = max(start_minutes, now.hour * 60 + now.minute + 1)  # no mostrar buses que ya salieron

    graph = load_graph()
    origin_vertex = graph.find_vertex(origin)
    destination_vertex = graph.find_vertex(destination)
    if origin_vertex is None or destination_vertex is None:
        return None
    origin = origin_vertex.name
    destination = destination_vertex.name

    schedules_tree = load_schedules(destination)
    heap = MinHeap()

    def add_to_heap(node):
        if origin_vertex.find_edge(node.route_id) is None:
            return
        # ordenar por precio y, a igual precio, por hora
        key = node.price * MINUTES_PER_DAY + node.minutes if sort_by == SORT_BY_PRICE else node.minutes
        heap.insert(key, node)

    schedules_tree.traverse_from(start_minutes, add_to_heap)

    taken_by_schedule = count_taken_seats_by_schedule(travel_date) if not heap.is_empty() else None
    departures = []
    while not heap.is_empty():
        node = heap.extract_min()
        edge = origin_vertex.find_edge(node.route_id)
        departures.append({
            "schedule_id": node.schedule_id,
            "company": edge.company,
            "origin": origin,
            "destination": destination,
            "departure_time": minutes_to_text(node.minutes),
            "duration_min": edge.weight,
            "price": node.price,
            "date": travel_date.isoformat(),
            "available_seats": node.seats - taken_by_schedule.get(node.schedule_id, 0),
        })
    return departures
