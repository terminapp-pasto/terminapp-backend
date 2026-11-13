"""Loads database data into the structures: graph, AVL tree and n-ary tree."""

from services.database import connect
from structs.avl_tree import AVLTree, minutes_to_text, time_to_minutes
from structs.graph import Graph
from structs.nary_tree import NaryNode, NaryTree

TERMINAL_NAME = "Terminal de Pasto"

ROUTES_QUERY = """
    SELECT r.id, o.name, d.name, r.duration_min, c.name
    FROM routes r
    JOIN destinations o ON o.id = r.origin_id
    JOIN destinations d ON d.id = r.destination_id
    JOIN companies c ON c.id = r.company_id
    WHERE EXISTS (SELECT 1 FROM schedules s WHERE s.route_id = r.id AND s.active)
    ORDER BY r.id;
"""

SCHEDULES_QUERY = """
    SELECT s.id, s.route_id, s.departure_time, s.price, s.seats
    FROM schedules s
    JOIN routes r ON r.id = s.route_id
    JOIN destinations d ON d.id = r.destination_id
    WHERE d.name = %s AND s.active
    ORDER BY s.departure_time;
"""

HIERARCHY_QUERY = """
    SELECT c.name, o.name, d.name, s.id, s.departure_time, s.price
    FROM schedules s
    JOIN routes r ON r.id = s.route_id
    JOIN companies c ON c.id = r.company_id
    JOIN destinations o ON o.id = r.origin_id
    JOIN destinations d ON d.id = r.destination_id
    WHERE s.active
    ORDER BY c.name, d.name, s.departure_time;
"""


def load_graph():
    """Route graph: each town is a vertex and each route an edge."""
    graph = Graph()
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(ROUTES_QUERY)
        for route_id, origin, destination, duration, company in cursor:
            graph.add_route(origin, destination, duration, company, route_id)
    return graph


def load_schedules(destination):
    """AVL tree with the departures to a destination, ordered by time."""
    tree = AVLTree()
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(SCHEDULES_QUERY, (destination,))
        for schedule_id, route_id, departure_time, price, seats in cursor:
            tree.insert(time_to_minutes(departure_time), schedule_id, route_id, price, seats)
    return tree


def load_terminal_hierarchy():
    """N-ary tree: Terminal → company → route → departure."""
    tree = NaryTree(TERMINAL_NAME)
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(HIERARCHY_QUERY)
        for company, origin, destination, schedule_id, departure_time, price in cursor:
            company_node = tree.root.get_or_create_child(company)
            route_node = company_node.get_or_create_child(f"{origin} → {destination}")
            label = f"{minutes_to_text(time_to_minutes(departure_time))}  ${price:,}"
            route_node.add_child(NaryNode(label, schedule_id))
    return tree
