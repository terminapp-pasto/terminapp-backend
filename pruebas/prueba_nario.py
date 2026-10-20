"""Pruebas del árbol n-ario (estructuras/nario.py)."""
import unittest

from estructuras.nario import ArbolNario


def nombres_de_hijos(nodo):
    nombres, hijo = [], nodo.primer_hijo
    while hijo is not None:
        nombres.append(hijo.nombre)
        hijo = hijo.siguiente_hermano
    return nombres


class PruebaNario(unittest.TestCase):
    def test_jerarquia_terminal_empresas_rutas(self):
        arbol = ArbolNario("Terminal de Pasto")
        bolivariano = arbol.raiz.obtener_hijo("EXPRESO BOLIVARIANO")
        bolivariano.obtener_hijo("Pasto → Cali")
        bolivariano.obtener_hijo("Pasto → Ipiales")
        arbol.raiz.obtener_hijo("TRANSIPIALES")
        self.assertEqual(nombres_de_hijos(arbol.raiz), ["EXPRESO BOLIVARIANO", "TRANSIPIALES"])
        self.assertEqual(nombres_de_hijos(bolivariano), ["Pasto → Cali", "Pasto → Ipiales"])

    def test_obtener_hijo_no_duplica(self):
        arbol = ArbolNario("Terminal")
        primero = arbol.raiz.obtener_hijo("TRANSANDONA")
        segundo = arbol.raiz.obtener_hijo("TRANSANDONA")
        self.assertIs(primero, segundo)
        self.assertEqual(len(nombres_de_hijos(arbol.raiz)), 1)

    def test_buscar_hijo_que_no_existe(self):
        self.assertIsNone(ArbolNario("Terminal").raiz.buscar_hijo("Nadie"))


if __name__ == "__main__":
    unittest.main()
