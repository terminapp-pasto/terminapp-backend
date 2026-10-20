"""Pruebas del montículo mínimo (estructuras/heap.py)."""
import random
import unittest

from estructuras.heap import Heap


class PruebaHeap(unittest.TestCase):
    def test_vacio(self):
        heap = Heap()
        self.assertTrue(heap.esta_vacio())
        self.assertIsNone(heap.extraer_minimo())

    def test_saca_siempre_el_menor(self):
        heap = Heap()
        for precio in (72000, 61000, 90000, 72000, 16000):
            heap.insertar(precio, precio)
        salida = [heap.extraer_minimo() for _ in range(5)]
        self.assertEqual(salida, [16000, 61000, 72000, 72000, 90000])
        self.assertTrue(heap.esta_vacio())

    def test_ordena_muchos_datos(self):
        datos = random.sample(range(100000), 500)
        heap = Heap()
        for dato in datos:
            heap.insertar(dato, dato)
        self.assertEqual([heap.extraer_minimo() for _ in datos], sorted(datos))

    def test_intercalar_insertar_y_extraer(self):
        heap = Heap()
        heap.insertar(5, "cinco")
        heap.insertar(3, "tres")
        self.assertEqual(heap.extraer_minimo(), "tres")
        heap.insertar(1, "uno")
        self.assertEqual(heap.extraer_minimo(), "uno")
        self.assertEqual(heap.extraer_minimo(), "cinco")


if __name__ == "__main__":
    unittest.main()
