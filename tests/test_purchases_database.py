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
SCRIPTS = ("01_tables.sql", "02_seed_data.sql", "03_purchases_and_chat.sql", "04_buses_and_seats.sql")
SESSION_ID = "cs_test_1"
DB_FOLDER = Path(__file__).resolve().parent.parent / "db"
CALI_SCHEDULE_ID = 19        # Bolivariano Pasto → Cali 20:30, 40-seat bus
LAST_SEAT = 40


def passenger(seat, name="Ana Pérez", document="1085123456"):
    return {"seat": seat, "name": name, "document": document}


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
        """Simulates opening the Stripe payment, with a session that lives `minutes` more."""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        purchases.mark_as_paying(purchase["user_id"], purchase["payment_id"], SESSION_ID, expires_at)

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
        self.reserve(self.ana, [12])
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE tickets SET created_at = NOW() - INTERVAL '20 minutes';")
        self.reserve(self.luis, [12])
        self.assertEqual(purchases.get_my_tickets(self.ana)[0]["status"], "EXPIRED")

    # ---------------- Payments that arrive late (audit finding 1) ----------------

    def test_open_payment_lives_as_long_as_its_stripe_session(self):
        purchase = self.reserve(self.ana, [13])
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE tickets SET created_at = NOW() - INTERVAL '40 minutes';")
        self.open_payment(purchase, minutes=10)   # the Stripe session is still open
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


if __name__ == "__main__":
    unittest.main()
