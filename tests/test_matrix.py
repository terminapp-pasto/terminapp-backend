"""Pruebas de la matriz con nodos enlazados (structs/matrix.py)."""
import unittest

from structs.graph import Graph, edit_distance
from structs.matrix import Matrix


class MatrixTest(unittest.TestCase):
    def test_initial_value(self):
        self.assertEqual(Matrix(3, 4, 0).get(2, 3), 0)

    def test_set_and_get(self):
        matrix = Matrix(3, 3)
        matrix.set(1, 2, 580)
        self.assertEqual(matrix.get(1, 2), 580)
        self.assertIsNone(matrix.get(2, 1))

    def test_out_of_range(self):
        matrix = Matrix(2, 2)
        with self.assertRaises(IndexError):
            matrix.get(2, 0)
        with self.assertRaises(IndexError):
            matrix.set(0, -1, 5)

    def test_travel_time_matrix_of_the_graph(self):
        graph = Graph()
        graph.add_route("Pasto", "Ipiales", 120, "A", 1)
        graph.add_route("Pasto", "Ipiales", 100, "B", 2)  # se queda la más rápida
        times = graph.travel_time_matrix()
        pasto = graph.find_vertex("Pasto").index
        ipiales = graph.find_vertex("Ipiales").index
        self.assertEqual(times.get(pasto, ipiales), 100)
        self.assertEqual(times.get(pasto, pasto), 0)
        self.assertIsNone(times.get(ipiales, pasto))

    def test_edit_distance_with_the_matrix(self):
        self.assertEqual(edit_distance("bodota", "Bogotá"), 1)   # cambiar d por g
        self.assertEqual(edit_distance("Sandona", "Sandoná"), 0)  # las tildes no cuentan
        self.assertEqual(edit_distance("moco", "Mocoa"), 1)      # falta una letra
        self.assertEqual(edit_distance("", "Cali"), 4)


if __name__ == "__main__":
    unittest.main()
