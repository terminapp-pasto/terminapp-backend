"""Pruebas del árbol AVL de horarios (estructuras/avl.py)."""
import unittest
from datetime import time

from estructuras.avl import ArbolAVL, a_minutos, a_texto


def altura_real(nodo):
    if nodo is None:
        return 0
    return 1 + max(altura_real(nodo.izquierdo), altura_real(nodo.derecho))


def esta_balanceado(nodo):
    if nodo is None:
        return True
    diferencia = abs(altura_real(nodo.izquierdo) - altura_real(nodo.derecho))
    return diferencia <= 1 and esta_balanceado(nodo.izquierdo) and esta_balanceado(nodo.derecho)


class PruebaAVL(unittest.TestCase):
    def test_conversion_de_horas(self):
        self.assertEqual(a_minutos(time(21, 30)), 1290)
        self.assertEqual(a_texto(1290), "21:30")
        self.assertEqual(a_texto(5), "00:05")

    def test_se_mantiene_balanceado_con_datos_ordenados(self):
        arbol = ArbolAVL()
        for minutos in range(0, 1440, 15):  # el peor caso para un árbol sin balanceo
            arbol.insertar(minutos, minutos, 1, 1000, 40)
        self.assertEqual(arbol.cantidad, 96)
        self.assertTrue(esta_balanceado(arbol.raiz))
        self.assertLessEqual(arbol.raiz.altura, 9)  # log2(96) ≈ 6.6

    def test_recorrer_desde_una_hora(self):
        arbol = ArbolAVL()
        for minutos in (1260, 360, 750, 1080, 1320, 600):
            arbol.insertar(minutos, minutos, 1, 1000, 40)
        vistos = []
        arbol.recorrer_desde(1080, lambda nodo: vistos.append(nodo.minutos))
        self.assertEqual(vistos, [1080, 1260, 1320])  # solo desde las 18:00 y en orden

    def test_acepta_horas_repetidas(self):
        arbol = ArbolAVL()
        arbol.insertar(600, 1, 1, 1000, 40)
        arbol.insertar(600, 2, 2, 2000, 40)
        vistos = []
        arbol.recorrer_desde(0, lambda nodo: vistos.append(nodo.horario_id))
        self.assertEqual(sorted(vistos), [1, 2])


if __name__ == "__main__":
    unittest.main()
