"""Tests for the directed weighted graph (structs/graph.py)."""
import unittest

from structs.graph import Graph, normalize


def sample_graph():
    graph = Graph()
    graph.add_route("Pasto", "Ipiales", 100, "CONTINENTAL BUS", 1)
    graph.add_route("Pasto", "Ipiales", 100, "EXPRESO BOLIVARIANO", 2)
    graph.add_route("Pasto", "Cali", 580, "TRANSIPIALES", 7)
    return graph


class GraphTest(unittest.TestCase):
    def test_normalize_removes_accents_and_uppercase(self):
        self.assertEqual(normalize("  Sandoná "), "sandona")
        self.assertEqual(normalize("BOGOTÁ"), "bogota")

    def test_does_not_repeat_vertices(self):
        self.assertEqual(sample_graph().size, 3)  # Pasto, Ipiales and Cali

    def test_finds_vertex_ignoring_accents(self):
        graph = Graph()
        graph.add_route("Pasto", "Sandoná", 135, "TRANSANDONA", 3)
        self.assertIsNotNone(graph.find_vertex("sandona"))
        self.assertIsNone(graph.find_vertex("Medellín"))

    def test_edges_are_directed(self):
        graph = sample_graph()
        self.assertIsNotNone(graph.find_vertex("Pasto").first_edge)
        self.assertIsNone(graph.find_vertex("Cali").first_edge)

    def test_counts_routes_of_a_vertex(self):
        edge, total = sample_graph().find_vertex("Pasto").first_edge, 0
        while edge is not None:
            total += 1
            edge = edge.next
        self.assertEqual(total, 3)

    def test_finds_edge_by_route(self):
        pasto = sample_graph().find_vertex("Pasto")
        self.assertEqual(pasto.find_edge(7).destination, "Cali")
        self.assertIsNone(pasto.find_edge(99))

    def test_fixes_typos(self):
        graph = Graph()
        for index, destination in enumerate(("Ipiales", "Sandoná", "Tumaco", "Mocoa", "Cali", "Bogotá")):
            graph.add_route("Pasto", destination, 100, "EMPRESA", index)
        self.assertEqual(graph.find_closest("bodota").name, "Bogotá")
        self.assertEqual(graph.find_closest("kali").name, "Cali")
        self.assertEqual(graph.find_closest("ipialez").name, "Ipiales")

    def test_does_not_invent_far_destinations(self):
        graph = sample_graph()
        self.assertIsNone(graph.find_closest("Medellín"))
        self.assertIsNone(graph.find_closest("xyz"))

    def test_describe_lists_routes(self):
        self.assertIn("Cali → (sin salidas)", sample_graph().describe())


if __name__ == "__main__":
    unittest.main()
