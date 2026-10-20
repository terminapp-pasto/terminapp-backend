"""Pruebas de las fechas de viaje: qué días se venden y qué fecha conoce la IA."""
import unittest
from datetime import datetime, timedelta

from ia.orquestador import instrucciones
from servicios.compra import ZONA_COLOMBIA, ErrorCompra, fecha_de_venta, hoy_en_colombia


class PruebaFechas(unittest.TestCase):
    def test_sin_fecha_es_hoy(self):
        self.assertEqual(fecha_de_venta(""), hoy_en_colombia())

    def test_se_vende_hasta_60_dias(self):
        en_60 = hoy_en_colombia() + timedelta(days=60)
        self.assertEqual(fecha_de_venta(en_60.isoformat()), en_60)
        with self.assertRaises(ErrorCompra):
            fecha_de_venta((en_60 + timedelta(days=1)).isoformat())

    def test_no_se_venden_fechas_pasadas_ni_mal_escritas(self):
        with self.assertRaises(ErrorCompra):
            fecha_de_venta((hoy_en_colombia() - timedelta(days=1)).isoformat())
        with self.assertRaises(ErrorCompra):
            fecha_de_venta("el sábado")

    def test_la_ia_conoce_hoy_y_los_proximos_dias(self):
        texto = instrucciones(datetime(2026, 10, 19, 23, 7, tzinfo=ZONA_COLOMBIA))
        self.assertIn("HOY es lunes 19 de octubre de 2026 (2026-10-19)", texto)
        self.assertIn("sábado 24 de octubre de 2026 (2026-10-24)", texto)
        self.assertIn("23:07", texto)


if __name__ == "__main__":
    unittest.main()
