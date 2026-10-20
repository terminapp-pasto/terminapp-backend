"""Pruebas de la pila (estructuras/pila.py)."""
import unittest

from estructuras.pila import Pila
from servicios.compra import LIBRE, apartar_en_mapa, armar_mapa


class PruebaPila(unittest.TestCase):
    def test_ultimo_en_entrar_primero_en_salir(self):
        pila = Pila()
        for asiento in (5, 6, 7):
            pila.apilar(asiento)
        self.assertEqual(pila.ver_cima(), 7)
        self.assertEqual([pila.desapilar() for _ in range(3)], [7, 6, 5])
        self.assertTrue(pila.esta_vacia())
        self.assertIsNone(pila.desapilar())

    def test_deshace_una_reserva_a_medias(self):
        mapa = armar_mapa(40, [12])
        self.assertEqual(apartar_en_mapa(mapa, [10, 11, 12, 13]), 12)
        for numero in (10, 11, 13):
            self.assertEqual(mapa.obtener(numero), LIBRE)  # la pila los liberó

    def test_reserva_completa(self):
        mapa = armar_mapa(40, [])
        self.assertIsNone(apartar_en_mapa(mapa, [1, 2]))
        self.assertEqual(mapa.obtener(1), "RESERVADO")


if __name__ == "__main__":
    unittest.main()
