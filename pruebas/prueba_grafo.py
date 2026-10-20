"""Pruebas del grafo dirigido y ponderado (estructuras/grafo.py)."""
import unittest

from estructuras.grafo import Grafo, normalizar


def grafo_de_ejemplo():
    grafo = Grafo()
    grafo.agregar_ruta("Pasto", "Ipiales", 100, "CONTINENTAL BUS", 1)
    grafo.agregar_ruta("Pasto", "Ipiales", 100, "EXPRESO BOLIVARIANO", 2)
    grafo.agregar_ruta("Pasto", "Cali", 580, "TRANSIPIALES", 7)
    return grafo


class PruebaGrafo(unittest.TestCase):
    def test_normalizar_quita_tildes_y_mayusculas(self):
        self.assertEqual(normalizar("  Sandoná "), "sandona")
        self.assertEqual(normalizar("BOGOTÁ"), "bogota")

    def test_no_repite_vertices(self):
        grafo = grafo_de_ejemplo()
        self.assertEqual(grafo.cantidad, 3)  # Pasto, Ipiales y Cali

    def test_busca_sin_importar_tildes(self):
        grafo = Grafo()
        grafo.agregar_ruta("Pasto", "Sandoná", 135, "TRANSANDONA", 3)
        self.assertIsNotNone(grafo.buscar_vertice("sandona"))
        self.assertIsNone(grafo.buscar_vertice("Medellín"))

    def test_las_aristas_son_dirigidas(self):
        grafo = grafo_de_ejemplo()
        self.assertIsNotNone(grafo.buscar_vertice("Pasto").primera_arista)
        self.assertIsNone(grafo.buscar_vertice("Cali").primera_arista)

    def test_cuenta_las_rutas_de_un_vertice(self):
        grafo = grafo_de_ejemplo()
        arista, total = grafo.buscar_vertice("Pasto").primera_arista, 0
        while arista is not None:
            total += 1
            arista = arista.siguiente
        self.assertEqual(total, 3)

    def test_busca_arista_por_ruta(self):
        pasto = grafo_de_ejemplo().buscar_vertice("Pasto")
        self.assertEqual(pasto.buscar_arista(7).destino, "Cali")
        self.assertIsNone(pasto.buscar_arista(99))


if __name__ == "__main__":
    unittest.main()
