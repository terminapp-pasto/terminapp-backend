"""Pruebas de la tabla hash con encadenamiento (estructuras/tabla_hash.py)."""
import random
import unittest

from estructuras.tabla_hash import TablaHash


class PruebaTablaHash(unittest.TestCase):
    def test_insertar_obtener_y_actualizar(self):
        tabla = TablaHash()
        tabla.insertar(12, "LIBRE")
        tabla.insertar(12, "OCUPADO")
        self.assertEqual(tabla.obtener(12), "OCUPADO")
        self.assertEqual(tabla.cantidad, 1)
        self.assertEqual(tabla.obtener(99, "NO"), "NO")

    def test_colisiones(self):
        tabla = TablaHash(2)  # pocas cubetas a propósito
        for clave in ("abc", "cab", "bca"):  # mismas letras, distintas claves
            tabla.insertar(clave, clave.upper())
        for clave in ("abc", "cab", "bca"):
            self.assertEqual(tabla.obtener(clave), clave.upper())

    def test_eliminar(self):
        tabla = TablaHash()
        tabla.insertar("a", 1)
        self.assertTrue(tabla.eliminar("a"))
        self.assertFalse(tabla.eliminar("a"))
        self.assertFalse(tabla.contiene("a"))
        self.assertEqual(tabla.cantidad, 0)

    def test_crece_sola_y_no_pierde_datos(self):
        tabla = TablaHash(4)
        claves = random.sample(range(10**6), 2000)
        for clave in claves:
            tabla.insertar(clave, clave * 2)
        self.assertGreater(tabla.capacidad, 2000 / 0.75)
        self.assertTrue(all(tabla.obtener(c) == c * 2 for c in claves))

    def test_recorrer(self):
        tabla = TablaHash()
        for numero in range(1, 41):
            tabla.insertar(numero, "LIBRE")
        vistos = []
        tabla.recorrer(lambda clave, valor: vistos.append(clave))
        self.assertEqual(sorted(vistos), list(range(1, 41)))


if __name__ == "__main__":
    unittest.main()
