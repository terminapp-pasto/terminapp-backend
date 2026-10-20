"""Pruebas de la cola (estructuras/cola.py)."""
import unittest
from datetime import datetime, timedelta, timezone

from estructuras.cola import Cola
from servicios.compra import buscar_vencidas


class PruebaCola(unittest.TestCase):
    def test_primero_en_entrar_primero_en_salir(self):
        cola = Cola()
        for tiquete in (1, 2, 3):
            cola.encolar(tiquete)
        self.assertEqual(cola.ver_frente(), 1)
        self.assertEqual([cola.desencolar() for _ in range(3)], [1, 2, 3])
        self.assertTrue(cola.esta_vacia())
        self.assertIsNone(cola.final)

    def test_se_puede_reusar_despues_de_vaciarla(self):
        cola = Cola()
        cola.encolar("a")
        cola.desencolar()
        cola.encolar("b")
        self.assertEqual(cola.desencolar(), "b")

    def test_vence_solo_las_reservas_viejas(self):
        ahora = datetime.now(timezone.utc)
        hace = lambda minutos: ahora - timedelta(minutes=minutos)
        pendientes = [
            (1, "RESERVADO", hace(50)),
            (2, "PAGANDO", hace(46)),   # más de 45: vence
            (3, "RESERVADO", hace(20)),  # más de 15: vence
            (4, "PAGANDO", hace(30)),   # todavía puede pagar
            (5, "RESERVADO", hace(5)),
        ]
        self.assertEqual(sorted(buscar_vencidas(pendientes, ahora)), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
