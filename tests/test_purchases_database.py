"""Purchase tests against a real PostgreSQL database, including concurrency.

They never use the production database. They only run when TEST_DATABASE_URL
points to an EMPTY, disposable database (for example a Neon branch named "testing"):
the tests drop and recreate every table in it.

    TEST_DATABASE_URL=postgresql://... python -m unittest tests.test_purchases_database
"""

import os
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
from services import purchases
from services.database import connect
from services.dates import today_in_colombia

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
SCRIPTS = (
    "01_tables.sql", "02_seed_data.sql", "03_purchases_and_chat.sql", "04_buses_and_seats.sql",
    "09_roles_and_settings.sql",
)
SESSION_ID = "cs_test_1"
DB_FOLDER = Path(__file__).resolve().parent.parent / "db"
CALI_SCHEDULE_ID = 19        # Bolivariano Pasto → Cali 20:30, 40-seat bus
LAST_SEAT = 40


def passenger(seat, name="Ana Pérez", document=None):
    # every seat gets its own document: the same person cannot travel twice in one purchase
    return {"seat": seat, "name": name, "document": document or f"10851234{seat:02d}"}


@unittest.skipUnless(TEST_DATABASE_URL, "Set TEST_DATABASE_URL to a disposable database to run these tests")
class PurchasesDatabaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TEST_DATABASE_URL == os.getenv("DATABASE_URL"):
            raise RuntimeError("TEST_DATABASE_URL cannot be the production database")
        cls.original_url = config.DATABASE_URL
        config.DATABASE_URL = TEST_DATABASE_URL
        cls.original_checker = purchases.stripe_session_checker

    @classmethod
    def tearDownClass(cls):
        config.DATABASE_URL = cls.original_url
        purchases.stripe_session_checker = cls.original_checker

    def setUp(self):
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
            for script in SCRIPTS:
                cursor.execute((DB_FOLDER / script).read_text(encoding="utf-8"))
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES "
                "('Ana', 'ana@prueba.co', 'x'), ('Luis', 'luis@prueba.co', 'x'), ('Eva', 'eva@prueba.co', 'x');"
            )
        self.ana, self.luis, self.eva = 1, 2, 3
        self.stripe_answer = purchases.SESSION_NOT_PAID
        self.checked_sessions = []

        def fake_stripe(session_id):
            self.checked_sessions.append(session_id)
            return self.stripe_answer

        purchases.stripe_session_checker = fake_stripe
        self.travel_date = today_in_colombia() + timedelta(days=1)

    def open_payment(self, purchase, minutes):
        """Simulates opening the Stripe payment, with `minutes` left before the purchase's deadline."""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=31)
        purchases.mark_as_paying(purchase["user_id"], purchase["payment_id"], SESSION_ID, expires_at)
        self.move_deadline(purchase, minutes)

    def move_deadline(self, purchase, minutes):
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE payments SET expires_at = NOW() + make_interval(mins => %s) WHERE id = %s;",
                (minutes, purchase["payment_id"]),
            )

    def reserve(self, user_id, seats):
        purchase = purchases.reserve_seats(
            user_id, CALI_SCHEDULE_ID, self.travel_date, [passenger(seat) for seat in seats]
        )
        purchase["user_id"] = user_id
        return purchase

    def fill_bus_except_last_seat(self):
        purchases.reserve_seats(
            self.eva, CALI_SCHEDULE_ID, self.travel_date, [passenger(n) for n in range(1, 6)]
        )
        with connect() as connection, connection.cursor() as cursor:
            # seats 6 to 39 are paid by other purchases
            cursor.execute("INSERT INTO payments (amount, status) VALUES (0, 'PAID') RETURNING id;")
            payment_id = cursor.fetchone()[0]
            cursor.execute(
                """INSERT INTO tickets (schedule_id, travel_date, status, passenger_id, seat_id, payment_id)
                   SELECT %s, %s, 'PAID', 1, st.id, %s
                   FROM seats st JOIN buses b ON b.id = st.bus_id
                   WHERE b.company_id = 3 AND st.number BETWEEN 6 AND 39;""",
                (CALI_SCHEDULE_ID, self.travel_date, payment_id),
            )

    # ---------------- Concurrency ----------------

    def test_two_people_take_the_last_seat_at_the_same_time(self):
        self.fill_bus_except_last_seat()
        seat_map = purchases.get_seat_map(CALI_SCHEDULE_ID, self.travel_date)
        self.assertEqual(seat_map["free_seats"], 1)

        start_together = threading.Barrier(2)
        results = {}

        def try_to_reserve(user_id):
            start_together.wait()  # both ask for seat 40 at the same instant
            try:
                results[user_id] = self.reserve(user_id, [LAST_SEAT])["status"]
            except purchases.PurchaseError as error:
                results[user_id] = error.status_code

        threads = [threading.Thread(target=try_to_reserve, args=(user,)) for user in (self.ana, self.luis)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sorted(results.values(), key=str), [409, "RESERVED"])
        self.assertEqual(purchases.get_seat_map(CALI_SCHEDULE_ID, self.travel_date)["free_seats"], 0)

    def test_many_people_race_for_the_same_seat(self):
        start_together = threading.Barrier(3)
        winners = []

        def try_to_reserve(user_id):
            start_together.wait()
            try:
                self.reserve(user_id, [10])
                winners.append(user_id)
            except purchases.PurchaseError:
                pass

        threads = [threading.Thread(target=try_to_reserve, args=(u,)) for u in (self.ana, self.luis, self.eva)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(winners), 1)

    # ---------------- Repeated pending purchase ----------------

    def test_reserving_again_the_same_trip_replaces_the_pending_purchase(self):
        first = self.reserve(self.ana, [1, 2])
        second = self.reserve(self.ana, [1, 2, 3])  # went back and changed their mind
        history = purchases.get_my_tickets(self.ana)
        pending = [p for p in history if p["status"] in purchases.PENDING_STATUSES]
        self.assertEqual([p["payment_id"] for p in pending], [second["payment_id"]])
        self.assertEqual(
            next(p for p in history if p["payment_id"] == first["payment_id"])["status"], "CANCELLED"
        )

    # ---------------- Failure paths ----------------

    def test_taken_seat_is_rejected_and_nothing_is_half_reserved(self):
        self.reserve(self.ana, [5])
        with self.assertRaises(purchases.PurchaseError) as context:
            self.reserve(self.luis, [4, 5, 6])
        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(purchases.get_my_tickets(self.luis), [])  # nothing was left half done

    def test_seat_outside_the_bus_or_past_date(self):
        with self.assertRaises(purchases.PurchaseError):
            self.reserve(self.ana, [41])
        with self.assertRaises(purchases.PurchaseError):
            purchases.reserve_seats(
                self.ana, CALI_SCHEDULE_ID, today_in_colombia() - timedelta(days=1), [passenger(1)]
            )

    def test_bad_passenger_data_never_reaches_the_database(self):
        for bad in (passenger(1, name="x" * 5000), passenger(1, document="12ab45"), passenger(1, name="4")):
            with self.assertRaises(purchases.PurchaseError):
                purchases.reserve_seats(self.ana, CALI_SCHEDULE_ID, self.travel_date, [bad])
        self.assertEqual(purchases.get_my_tickets(self.ana), [])

    def test_another_user_cannot_touch_my_purchase(self):
        purchase = self.reserve(self.ana, [7])
        with self.assertRaises(purchases.PurchaseError) as context:
            purchases.cancel_purchase(self.luis, purchase["payment_id"])
        self.assertEqual(context.exception.status_code, 404)

    def test_cancel_frees_the_seats_and_cannot_be_paid(self):
        purchase = self.reserve(self.ana, [8, 9])
        status, _ = purchases.cancel_purchase(self.ana, purchase["payment_id"])
        self.assertEqual(status, "CANCELLED")
        self.reserve(self.luis, [8, 9])  # the seats are free again
        with self.assertRaises(purchases.PurchaseError):
            purchases.get_payment_details(self.ana, purchase["payment_id"])

    def test_paid_purchase_cannot_be_cancelled(self):
        purchase = self.reserve(self.ana, [11])
        self.open_payment(purchase, minutes=31)
        self.assertEqual(purchases.mark_as_paid(self.ana, purchase["payment_id"]), "PAID")
        self.assertEqual(purchases.mark_as_paid(self.ana, purchase["payment_id"]), "PAID")  # reloading the page
        with self.assertRaises(purchases.PurchaseError):
            purchases.cancel_purchase(self.ana, purchase["payment_id"])

    def test_old_reservations_expire_and_free_the_seat(self):
        purchase = self.reserve(self.ana, [12])
        self.move_deadline(purchase, -1)
        self.reserve(self.luis, [12])
        self.assertEqual(purchases.get_my_tickets(self.ana)[0]["status"], "EXPIRED")

    # ---------------- Payments that arrive late (audit finding 1) ----------------

    def test_open_payment_lives_until_its_deadline(self):
        purchase = self.reserve(self.ana, [13])
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE tickets SET created_at = NOW() - INTERVAL '40 minutes';")
        self.open_payment(purchase, minutes=3)    # still on time
        self.assertEqual(purchases.get_my_tickets(self.ana)[0]["status"], "PAYING")
        self.assertEqual(self.checked_sessions, [])

    def test_unpaid_session_is_closed_and_the_seat_freed(self):
        purchase = self.reserve(self.ana, [14])
        self.open_payment(purchase, minutes=-1)   # the session already ended
        self.reserve(self.luis, [14])              # the seat is free again
        self.assertEqual(self.checked_sessions, [SESSION_ID])
        self.assertEqual(purchases.get_my_tickets(self.ana)[0]["status"], "EXPIRED")

    def test_paid_session_is_confirmed_instead_of_expired(self):
        purchase = self.reserve(self.ana, [15])
        self.open_payment(purchase, minutes=-1)
        self.stripe_answer = purchases.SESSION_PAID   # paid at the last second, user never came back
        with self.assertRaises(purchases.PurchaseError):
            self.reserve(self.luis, [15])
        self.assertEqual(purchases.get_my_tickets(self.ana)[0]["status"], "PAID")

    def test_stripe_down_keeps_the_seats(self):
        purchase = self.reserve(self.ana, [16])
        self.open_payment(purchase, minutes=-1)
        self.stripe_answer = purchases.SESSION_UNKNOWN
        self.assertEqual(purchases.get_my_tickets(self.ana)[0]["status"], "PAYING")

    def test_late_payment_recovers_free_seats(self):
        purchase = self.reserve(self.ana, [17])
        self.open_payment(purchase, minutes=-1)
        purchases.get_my_tickets(self.ana)            # expires it
        status = purchases.confirm_payment(purchase["payment_id"])   # webhook arrives late
        self.assertEqual(status, "PAID")

    def test_late_payment_for_sold_seats_asks_for_a_refund(self):
        purchase = self.reserve(self.ana, [18])
        self.open_payment(purchase, minutes=-1)
        self.reserve(self.luis, [18])                 # someone else bought the seat
        with self.assertRaises(purchases.SeatsLostError) as context:
            purchases.confirm_payment(purchase["payment_id"])
        self.assertEqual(context.exception.stripe_session_id, SESSION_ID)
        self.assertEqual(purchases.get_my_tickets(self.luis)[0]["status"], "RESERVED")

    # ---------------- Seat hoarding (audit finding 2) ----------------

    def test_one_user_cannot_hold_more_than_two_unpaid_purchases(self):
        purchases.reserve_seats(self.ana, 18, self.travel_date, [passenger(1)])
        purchases.reserve_seats(self.ana, 19, self.travel_date, [passenger(1)])
        with self.assertRaises(purchases.PurchaseError) as context:
            purchases.reserve_seats(self.ana, 20, self.travel_date, [passenger(1)])
        self.assertEqual(context.exception.status_code, 409)
        purchases.reserve_seats(self.ana, 19, self.travel_date, [passenger(2)])   # same trip replaces: allowed

    def test_history_groups_passengers_by_purchase(self):
        self.reserve(self.ana, [20, 21])
        history = purchases.get_my_tickets(self.ana)
        self.assertEqual(len(history), 1)
        self.assertEqual([t["seat"] for t in history[0]["tickets"]], [20, 21])
        self.assertEqual(history[0]["total"], history[0]["unit_price"] * 2)

    def test_document_type_is_saved_and_shown_in_the_history(self):
        traveler = {"seat": 23, "name": "John Smith", "document_type": "PA", "document": "X1234567"}
        reservation = purchases.reserve_seats(self.ana, 18, self.travel_date, [traveler, passenger(24)])
        self.assertEqual([p["document_type"] for p in reservation["passengers"]], ["PA", "CC"])
        tickets = purchases.get_my_tickets(self.ana)[0]["tickets"]
        self.assertEqual([(t["document_type"], t["document"]) for t in tickets], [("PA", "X1234567"), ("CC", "1085123424")])

    def test_each_purchase_gets_its_own_booking_code(self):
        first = self.reserve(self.ana, [22])
        second = purchases.reserve_seats(self.luis, 18, self.travel_date, [passenger(1)])
        self.assertRegex(first["booking_code"], r"^[A-Z2-9]{6}$")
        self.assertNotEqual(first["booking_code"], second["booking_code"])
        self.assertEqual(purchases.get_my_tickets(self.ana)[0]["booking_code"], first["booking_code"])


    # ---------------- Settings of each company ----------------

    def set_company(self, **settings):
        with connect() as connection, connection.cursor() as cursor:
            for column, value in settings.items():
                cursor.execute(f"UPDATE companies SET {column} = %s WHERE id = 3;", (value,))

    def test_the_hold_lasts_the_minutes_the_company_chose(self):
        self.set_company(reservation_minutes=7)
        purchase = self.reserve(self.ana, [25])
        self.assertEqual(purchase["reservation_minutes"], 7)
        left = datetime.fromisoformat(purchase["expires_at"]) - datetime.now(timezone.utc)
        self.assertTrue(timedelta(minutes=6) < left <= timedelta(minutes=7), left)
        self.open_payment(purchase, minutes=-1)   # the Stripe session lives 31 minutes, the hold does not
        self.reserve(self.luis, [25])
        self.assertEqual(purchases.get_my_tickets(self.ana)[0]["status"], "EXPIRED")

    def test_opening_the_payment_keeps_the_short_deadline(self):
        self.set_company(reservation_minutes=5)
        purchase = self.reserve(self.ana, [26])
        stripe_expiration = datetime.now(timezone.utc) + timedelta(minutes=31)
        purchases.mark_as_paying(self.ana, purchase["payment_id"], SESSION_ID, stripe_expiration)
        details = purchases.get_payment_details(self.ana, purchase["payment_id"])
        left = datetime.fromisoformat(details["expires_at"]) - datetime.now(timezone.utc)
        self.assertLess(left, timedelta(minutes=6))

    def test_each_company_sets_its_seats_per_purchase(self):
        self.set_company(max_seats_per_purchase=2)
        with self.assertRaises(purchases.PurchaseError) as context:
            self.reserve(self.ana, [1, 2, 3])
        self.assertIn("máximo 2", context.exception.message)
        self.set_company(max_seats_per_purchase=7)
        self.assertEqual(len(self.reserve(self.ana, range(1, 8))["seats"]), 7)

    def test_same_document_twice_is_rejected(self):
        with self.assertRaises(purchases.PurchaseError) as context:
            self.reserve_with([passenger(1, document="1085123456"), passenger(2, document="1.085.123.456")])
        self.assertIn("mismo documento", context.exception.message)

    def reserve_with(self, travellers, phone=None):
        return purchases.reserve_seats(self.ana, CALI_SCHEDULE_ID, self.travel_date, travellers, phone)

    def test_phone_and_luggage_are_saved_and_shown(self):
        travellers = [dict(passenger(27), checked_bags=2), passenger(28)]
        purchase = self.reserve_with(travellers, "+57 300 123 4567")
        self.assertEqual(purchase["contact_phone"], "3001234567")
        history = purchases.get_my_tickets(self.ana)[0]
        self.assertEqual(history["contact_phone"], "3001234567")
        self.assertEqual([t["checked_bags"] for t in history["tickets"]], [2, 0])
        for bad_phone in ("12345", "2001234567"):
            with self.assertRaises(purchases.PurchaseError):
                self.reserve_with([passenger(29)], bad_phone)
        with self.assertRaises(purchases.PurchaseError):
            self.reserve_with([dict(passenger(29), checked_bags=3)])

    def test_a_new_document_type_from_the_database_is_accepted(self):
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO document_types (code, name, min_length, max_length, allows_letters) "
                "VALUES ('PT', 'Permiso por protección temporal', 6, 10, FALSE);"
            )
            cursor.execute("UPDATE document_types SET active = FALSE WHERE code = 'TI';")
        purchase = self.reserve_with([dict(passenger(30), document_type="PT", document="123456")])
        self.assertEqual(purchase["passengers"][0]["document_type"], "PT")
        with self.assertRaises(purchases.PurchaseError):
            self.reserve_with([dict(passenger(31), document_type="TI", document="10851234567")])


if __name__ == "__main__":
    unittest.main()
