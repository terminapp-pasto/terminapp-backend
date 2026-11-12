"""Tests for form validation (services/validation.py) and passengers."""
import unittest

from services.purchases import (
    BOOKING_CODE_ALPHABET, BOOKING_CODE_LENGTH, MAX_SEATS_PER_PURCHASE, PurchaseError, clean_passengers,
    generate_booking_code,
)
from services.validation import (
    is_valid_document, is_valid_email, is_valid_name, is_valid_password, normalize_spaces,
)


class ValidationTest(unittest.TestCase):
    def test_valid_names(self):
        for name in ("Ana", "María José Pérez", "Ñoño Muñoz", "O'Neil", "Ana-Lucía", "Jhonatan Mideros"):
            self.assertTrue(is_valid_name(name), name)

    def test_invalid_names(self):
        for name in ("", "Al", "4", "Juan 2", "Ana@", "<script>", " Ana", "a" * 51, "Ana" * 1000):
            self.assertFalse(is_valid_name(name), name[:20])

    def test_document_only_digits(self):
        self.assertTrue(is_valid_document("1085123456"))
        for document in ("", "1234", "12a456", "1.085.123", "1" * 13, "9" * 10000):
            self.assertFalse(is_valid_document(document), document[:20])

    def test_email_and_password_limits(self):
        self.assertTrue(is_valid_email("ana@correo.co"))
        self.assertFalse(is_valid_email("ana@correo"))
        self.assertFalse(is_valid_email("a" * 95 + "@b.co1"))
        self.assertTrue(is_valid_password("12345678"))
        self.assertFalse(is_valid_password("1234567"))
        self.assertFalse(is_valid_password("x" * 73))

    def test_normalize_spaces(self):
        self.assertEqual(normalize_spaces("  Ana   María  "), "Ana María")


class PassengersTest(unittest.TestCase):
    def passenger(self, seat, name="Ana Pérez", document="1085123456"):
        return {"seat": seat, "name": name, "document": document}

    def test_one_passenger_per_seat(self):
        cleaned = clean_passengers([self.passenger(3), self.passenger(4, "Luis  Gómez", " 12345 ")])
        self.assertEqual(cleaned, [(3, "Ana Pérez", "1085123456"), (4, "Luis Gómez", "12345")])

    def test_rejects_empty_too_many_or_repeated_seats(self):
        with self.assertRaises(PurchaseError):
            clean_passengers([])
        with self.assertRaises(PurchaseError):
            clean_passengers([self.passenger(n) for n in range(1, MAX_SEATS_PER_PURCHASE + 2)])
        with self.assertRaises(PurchaseError):
            clean_passengers([self.passenger(5), self.passenger(5)])

    def test_says_which_passenger_is_wrong(self):
        with self.assertRaises(PurchaseError) as context:
            clean_passengers([self.passenger(1), self.passenger(2, document="abc")])
        self.assertIn("Pasajero 2", context.exception.message)


class BookingCodeTest(unittest.TestCase):
    def test_code_has_six_unambiguous_characters(self):
        for _ in range(200):
            code = generate_booking_code()
            self.assertEqual(len(code), BOOKING_CODE_LENGTH)
            self.assertTrue(all(character in BOOKING_CODE_ALPHABET for character in code))
            self.assertFalse(set(code) & set("O0I1"))

    def test_codes_are_not_repeated(self):
        codes = {generate_booking_code() for _ in range(1000)}
        self.assertGreater(len(codes), 995)


if __name__ == "__main__":
    unittest.main()
