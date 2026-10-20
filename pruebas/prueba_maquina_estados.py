"""Pruebas de la máquina de estados de la compra (estructuras/maquina_estados.py)."""
import unittest

from estructuras.maquina_estados import (
    CANCELADO, ELIGIENDO, PAGADO, PAGANDO, RESERVADO, VENCIDO, ErrorTransicion, maquina_de_compra,
)


class PruebaMaquinaEstados(unittest.TestCase):
    def test_camino_feliz(self):
        maquina = maquina_de_compra()
        self.assertEqual(maquina.estado, ELIGIENDO)
        self.assertEqual(maquina.disparar("reservar"), RESERVADO)
        self.assertEqual(maquina.disparar("ir_a_pagar"), PAGANDO)
        self.assertEqual(maquina.disparar("confirmar_pago"), PAGADO)

    def test_un_tiquete_pagado_no_cambia(self):
        maquina = maquina_de_compra(PAGADO)
        for evento in ("cancelar", "vencer", "reservar", "ir_a_pagar"):
            self.assertFalse(maquina.puede(evento))
            with self.assertRaises(ErrorTransicion):
                maquina.disparar(evento)
        self.assertEqual(maquina.estado, PAGADO)

    def test_cancelar_y_vencer(self):
        self.assertEqual(maquina_de_compra(RESERVADO).disparar("cancelar"), CANCELADO)
        self.assertEqual(maquina_de_compra(PAGANDO).disparar("vencer"), VENCIDO)

    def test_no_se_puede_pagar_sin_reservar(self):
        with self.assertRaises(ErrorTransicion):
            maquina_de_compra(ELIGIENDO).disparar("confirmar_pago")


if __name__ == "__main__":
    unittest.main()
