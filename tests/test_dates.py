"""Pruebas de las fechas de viaje: qué días se venden y qué fecha conoce la IA."""
import unittest
from datetime import datetime, timedelta

from ai.orchestrator import build_system_instructions
from services.dates import COLOMBIA_TIMEZONE, InvalidDateError, parse_travel_date, today_in_colombia


class DatesTest(unittest.TestCase):
    def test_empty_date_means_today(self):
        self.assertEqual(parse_travel_date(""), today_in_colombia())

    def test_sells_up_to_60_days_ahead(self):
        in_60_days = today_in_colombia() + timedelta(days=60)
        self.assertEqual(parse_travel_date(in_60_days.isoformat()), in_60_days)
        with self.assertRaises(InvalidDateError):
            parse_travel_date((in_60_days + timedelta(days=1)).isoformat())

    def test_rejects_past_and_badly_written_dates(self):
        with self.assertRaises(InvalidDateError):
            parse_travel_date((today_in_colombia() - timedelta(days=1)).isoformat())
        with self.assertRaises(InvalidDateError):
            parse_travel_date("el sábado")
        with self.assertRaises(InvalidDateError):
            parse_travel_date("2026-02-30")

    def test_ai_knows_today_and_next_days(self):
        text = build_system_instructions(datetime(2026, 10, 19, 23, 7, tzinfo=COLOMBIA_TIMEZONE))
        self.assertIn("HOY es lunes 19 de octubre de 2026 (2026-10-19)", text)
        self.assertIn("sábado 24 de octubre de 2026 (2026-10-24)", text)
        self.assertIn("23:07", text)


if __name__ == "__main__":
    unittest.main()
