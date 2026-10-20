"""Pruebas de la matriz con nodos enlazados (estructuras/matriz.py)."""
import unittest

from estructuras.grafo import Grafo, distancia_de_edicion
from estructuras.matriz import Matriz


class PruebaMatriz(unittest.TestCase):
    def test_valor_inicial(self):
        matriz = Matriz(3, 4, 0)
        self.assertEqual(matriz.obtener(2, 3), 0)

    def test_asignar_y_obtener(self):
        matriz = Matriz(3, 3)
        matriz.asignar(1, 2, 580)
        self.assertEqual(matriz.obtener(1, 2), 580)
        self.assertIsNone(matriz.obtener(2, 1))

    def test_fuera_de_rango(self):
        matriz = Matriz(2, 2)
        with self.assertRaises(IndexError):
            matriz.obtener(2, 0)
        with self.assertRaises(IndexError):
            matriz.asignar(0, -1, 5)

    def test_matriz_de_tiempos_del_grafo(self):
        grafo = Grafo()
        grafo.agregar_ruta("Pasto", "Ipiales", 120, "A", 1)
        grafo.agregar_ruta("Pasto", "Ipiales", 100, "B", 2)  # se queda la más rápida
        tiempos = grafo.matriz_de_tiempos()
        pasto = grafo.buscar_vertice("Pasto").indice
        ipiales = grafo.buscar_vertice("Ipiales").indice
        self.assertEqual(tiempos.obtener(pasto, ipiales), 100)
        self.assertEqual(tiempos.obtener(pasto, pasto), 0)
        self.assertIsNone(tiempos.obtener(ipiales, pasto))

    def test_distancia_de_edicion_con_la_matriz(self):
        self.assertEqual(distancia_de_edicion("bodota", "Bogotá"), 1)  # cambiar d por g
        self.assertEqual(distancia_de_edicion("Sandona", "Sandoná"), 0)  # las tildes no cuentan
        self.assertEqual(distancia_de_edicion("moco", "Mocoa"), 1)  # falta una letra
        self.assertEqual(distancia_de_edicion("", "Cali"), 4)


if __name__ == "__main__":
    unittest.main()
