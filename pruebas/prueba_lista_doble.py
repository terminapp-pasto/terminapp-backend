"""Pruebas de la lista doblemente enlazada (estructuras/lista_doble.py)."""
import unittest

from estructuras.lista_doble import ListaDoble
from servicios.compra import historial


def adelante(lista):
    datos = []
    lista.recorrer_adelante(datos.append)
    return datos


def atras(lista):
    datos = []
    lista.recorrer_atras(datos.append)
    return datos


class PruebaListaDoble(unittest.TestCase):
    def test_recorrer_en_los_dos_sentidos(self):
        lista = ListaDoble()
        for dato in (2, 3):
            lista.agregar_al_final(dato)
        lista.agregar_al_inicio(1)
        self.assertEqual(adelante(lista), [1, 2, 3])
        self.assertEqual(atras(lista), [3, 2, 1])

    def test_eliminar_en_medio_y_en_los_extremos(self):
        lista = ListaDoble()
        nodos = [lista.agregar_al_final(n) for n in range(5)]
        lista.eliminar_nodo(nodos[2])
        lista.eliminar_nodo(nodos[0])
        lista.eliminar_nodo(nodos[4])
        self.assertEqual(adelante(lista), [1, 3])
        self.assertEqual(atras(lista), [3, 1])
        self.assertEqual(lista.cantidad, 2)

    def test_historial_de_tiquetes(self):
        tiquetes = [{"id": 3}, {"id": 2}, {"id": 1}]  # vienen del más reciente al más antiguo
        self.assertEqual([t["id"] for t in historial(iter(tiquetes))], [3, 2, 1])
        self.assertEqual([t["id"] for t in historial(iter(tiquetes), "antiguos")], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
