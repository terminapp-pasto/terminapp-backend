"""Admin panel tests against a disposable PostgreSQL database (same rules as
test_purchases_database.py: they only run with TEST_DATABASE_URL and wipe that database).

    TEST_DATABASE_URL=postgresql://... python -m unittest tests.test_admin_database
"""

import os
import unittest
from unittest import mock
from datetime import timedelta
from pathlib import Path

from fastapi import HTTPException

import config
from routes.dependencies import company_scope, require_admin, require_staff

READ_REQUEST = mock.Mock(method="GET")  # the panel only limits changes (POST)
from services import admin, purchases
from services.database import connect
from services.dates import today_in_colombia
from services.users import find_user_by_email, find_user_by_id, upsert_user

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
DB_FOLDER = Path(__file__).resolve().parent.parent / "db"
SCRIPTS = (
    "01_tables.sql", "02_seed_data.sql", "03_purchases_and_chat.sql", "04_buses_and_seats.sql",
    "09_roles_and_settings.sql", "10_colombia_routes.sql", "11_app_settings.sql",
)
BOLIVARIANO = 3
CONTINENTAL = 4
CALI_ROUTE = 6               # Bolivariano Pasto → Cali
CALI_SCHEDULE_ID = 19


@unittest.skipUnless(TEST_DATABASE_URL, "Set TEST_DATABASE_URL to a disposable database to run these tests")
class AdminDatabaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TEST_DATABASE_URL == os.getenv("DATABASE_URL"):
            raise RuntimeError("TEST_DATABASE_URL cannot be the production database")
        cls.original_url = config.DATABASE_URL
        config.DATABASE_URL = TEST_DATABASE_URL

    @classmethod
    def tearDownClass(cls):
        config.DATABASE_URL = cls.original_url

    def setUp(self):
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
            for script in SCRIPTS:
                cursor.execute((DB_FOLDER / script).read_text(encoding="utf-8"))
            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role, company_id) VALUES "
                "('Admin', 'admin@prueba.co', 'x', 'admin', NULL), "
                "('Bolivariano', 'bol@prueba.co', 'x', 'company', 3), "
                "('Ana', 'ana@prueba.co', 'x', 'user', NULL);"
            )
        self.admin, self.company, self.traveller = (find_user_by_id(n) for n in (1, 2, 3))
        self.tomorrow = today_in_colombia() + timedelta(days=1)

    # ---------------- Roles ----------------

    def test_roles_protect_the_panel(self):
        self.assertIsNone(company_scope(require_staff(READ_REQUEST, self.admin)))
        self.assertEqual(company_scope(require_staff(READ_REQUEST, self.company)), BOLIVARIANO)
        with self.assertRaises(HTTPException) as context:
            require_staff(READ_REQUEST, self.traveller)
        self.assertEqual(context.exception.status_code, 403)
        with self.assertRaises(HTTPException):
            require_admin(READ_REQUEST, self.company)

    def test_login_lookup_brings_the_role(self):
        user = find_user_by_email("bol@prueba.co")
        self.assertEqual((user["role"], user["company"], user["password_hash"]), ("company", "EXPRESO BOLIVARIANO", "x"))
        upsert_user("Jefe", "jefe@prueba.co", "y", "admin")
        upsert_user("Jefe", "jefe@prueba.co", "z")            # the test account keeps its role
        self.assertEqual(find_user_by_email("jefe@prueba.co")["role"], "admin")

    def test_admin_gives_and_takes_roles(self):
        changed = admin.set_user_role(1, 3, "company", CONTINENTAL)
        self.assertEqual(find_user_by_id(3)["company"], "CONTINENTAL BUS")
        self.assertEqual(changed["role"], "company")
        admin.set_user_role(1, 3, "user")
        self.assertIsNone(find_user_by_id(3)["company_id"])
        with self.assertRaises(admin.AdminError):
            admin.set_user_role(1, 3, "company")          # needs a company
        with self.assertRaises(admin.AdminError):
            admin.set_user_role(1, 1, "user")             # cannot lock themselves out
        self.assertEqual([u["email"] for u in admin.find_users("ana")], ["ana@prueba.co"])

    # ---------------- Company settings ----------------

    def test_company_changes_its_own_settings_only(self):
        changed = admin.update_company_settings(BOLIVARIANO, BOLIVARIANO, reservation_minutes=6)
        self.assertEqual(changed["reservation_minutes"], 6)
        self.assertEqual(changed["max_seats_per_purchase"], 5)
        with self.assertRaises(admin.AdminError) as context:
            admin.update_company_settings(BOLIVARIANO, CONTINENTAL, reservation_minutes=6)
        self.assertEqual(context.exception.status_code, 404)
        for bad in (4, 31):
            with self.assertRaises(admin.AdminError):
                admin.update_company_settings(None, BOLIVARIANO, reservation_minutes=bad)
        self.assertEqual([c["name"] for c in admin.list_companies(BOLIVARIANO)], ["EXPRESO BOLIVARIANO"])
        self.assertEqual(len(admin.list_companies()), 4)

    def test_new_settings_reach_the_purchase(self):
        admin.update_company_settings(None, BOLIVARIANO, max_seats=1, reservation_minutes=8)
        seat_map = purchases.get_seat_map(CALI_SCHEDULE_ID, self.tomorrow)
        self.assertEqual(seat_map["departure"]["max_seats_per_purchase"], 1)
        self.assertEqual(seat_map["departure"]["reservation_minutes"], 8)

    # ---------------- Buses, routes and departures ----------------

    def test_new_bus_gets_its_seats_and_capacity(self):
        bus = admin.create_bus(BOLIVARIANO, BOLIVARIANO, "exb 777", 30)
        self.assertEqual(bus["plate"], "EXB-777")
        with self.assertRaises(admin.AdminError):
            admin.create_bus(None, BOLIVARIANO, "EXB-777", 30)       # repeated plate
        with self.assertRaises(admin.AdminError):
            admin.create_bus(BOLIVARIANO, CONTINENTAL, "CTB-999", 30)  # another company
        changed = admin.update_departure(None, CALI_SCHEDULE_ID, bus_id=bus["id"])
        self.assertEqual(changed["bus_id"], bus["id"])
        seat_map = purchases.get_seat_map(CALI_SCHEDULE_ID, self.tomorrow)
        self.assertEqual(len(seat_map["seats"]), 30)

    def test_bus_cannot_change_once_seats_are_sold(self):
        bus = admin.create_bus(None, BOLIVARIANO, "EXB-555", 20)
        purchases.reserve_seats(3, CALI_SCHEDULE_ID, self.tomorrow,
                                [{"seat": 1, "name": "Ana Pérez", "document": "1085123456"}])
        with self.assertRaises(admin.AdminError) as context:
            admin.update_departure(None, CALI_SCHEDULE_ID, bus_id=bus["id"])
        self.assertEqual(context.exception.status_code, 409)

    def test_route_price_and_old_purchases_keep_their_price(self):
        purchase = purchases.reserve_seats(3, CALI_SCHEDULE_ID, self.tomorrow,
                                           [{"seat": 2, "name": "Ana Pérez", "document": "1085123456"}])
        result = admin.set_route_price(BOLIVARIANO, CALI_ROUTE, 99000)
        self.assertEqual(result["departures_changed"], 4)
        route = next(r for r in admin.list_routes(BOLIVARIANO) if r["id"] == CALI_ROUTE)
        self.assertEqual({d["price"] for d in route["departures"]}, {99000})
        details = purchases.get_payment_details(3, purchase["payment_id"])
        self.assertEqual(details["unit_price"], purchase["total"])     # Stripe charges what was reserved
        with self.assertRaises(admin.AdminError):
            admin.set_route_price(CONTINENTAL, CALI_ROUTE, 99000)      # not their route
        with self.assertRaises(admin.AdminError):
            admin.set_route_price(None, CALI_ROUTE, 50)

    def test_new_route_and_departure_appear_in_the_search(self):
        from services.search import search_departures
        with self.assertRaises(admin.AdminError):
            admin.create_route(BOLIVARIANO, BOLIVARIANO, "Leticia", 600)   # only the admin adds towns
        route = admin.create_route(None, BOLIVARIANO, "leticia", 600)
        self.assertEqual(route["destination"], "Leticia")
        bus_id = admin.list_buses(BOLIVARIANO)[0]["id"]
        departure = admin.create_departure(BOLIVARIANO, route["id"], "6:45", 300000, bus_id)
        self.assertEqual(departure["departure_time"], "06:45")
        found = search_departures("Pasto", "Leticia", 0, "time", self.tomorrow)
        self.assertEqual([(d["departure_time"], d["price"], d["available_seats"]) for d in found],
                         [("06:45", 300000, 40)])
        admin.update_departure(None, departure["id"], active=False)
        self.assertIsNone(search_departures("Pasto", "Leticia", 0, "time", self.tomorrow))
        with self.assertRaises(purchases.PurchaseError):
            purchases.reserve_seats(3, departure["id"], self.tomorrow,
                                    [{"seat": 1, "name": "Ana Pérez", "document": "1085123456"}])

    def test_colombia_routes_are_loaded(self):
        destinations = {d["name"] for d in admin.list_destinations()}
        self.assertTrue({"Medellín", "Popayán", "Barranquilla", "Villavicencio"} <= destinations)

    # ---------------- Document types ----------------

    def test_document_types(self):
        created = admin.create_document_type("pt", "Permiso temporal", 6, 10, False)
        self.assertEqual(created["code"], "PT")
        with self.assertRaises(admin.AdminError):
            admin.create_document_type("PT", "Otro", 6, 10, False)
        with self.assertRaises(admin.AdminError):
            admin.create_document_type("P1", "Otro", 6, 10, False)
        with self.assertRaises(admin.AdminError):
            admin.create_document_type("XY", "Otro", 9, 6, False)
        admin.set_document_type_active("TI", False)
        self.assertNotIn("TI", [t["code"] for t in admin.list_document_types() if t["active"]])
        for code in ("CC", "CE", "PA"):
            admin.set_document_type_active(code, False)
        with self.assertRaises(admin.AdminError):
            admin.set_document_type_active("PT", False)                 # at least one must stay on

    # ---------------- Occupancy ----------------

    def test_occupancy_counts_sold_and_held_seats(self):
        purchase = purchases.reserve_seats(3, CALI_SCHEDULE_ID, self.tomorrow, [
            {"seat": 1, "name": "Ana Pérez", "document": "1085123456"},
            {"seat": 2, "name": "Luis Gómez", "document": "1085123457"},
        ])
        purchases.mark_as_paying(3, purchase["payment_id"], "cs_test_x", purchase["expires_at"])
        purchases.confirm_payment(purchase["payment_id"])
        purchases.reserve_seats(3, 20, self.tomorrow, [{"seat": 5, "name": "Ana Pérez", "document": "1085123456"}])

        report = admin.occupancy(BOLIVARIANO, self.tomorrow)
        cali = next(d for d in report["departures"] if d["schedule_id"] == CALI_SCHEDULE_ID)
        self.assertEqual((cali["sold"], cali["held"], cali["free"]), (2, 0, 38))
        self.assertEqual(cali["revenue"], purchase["total"])
        other = next(d for d in report["departures"] if d["schedule_id"] == 20)
        self.assertEqual((other["sold"], other["held"]), (0, 1))
        self.assertEqual({d["company"] for d in report["departures"]}, {"EXPRESO BOLIVARIANO"})
        self.assertEqual(report["totals"]["sold"], 2)
        self.assertGreater(len(admin.occupancy(None, self.tomorrow)["departures"]), len(report["departures"]))


    # ---------------- AI assistant ----------------

    def test_assistant_only_proposes_changes(self):
        from ai import admin_assistant
        replies = iter([
            {"role": "model", "parts": [{"functionCall": {"name": "list_routes", "args": {"destination": "cali"}}}]},
            {"role": "model", "parts": [{"functionCall": {"name": "propose_route_price",
                                                          "args": {"route_id": CALI_ROUTE, "price": 85000}}}]},
            {"role": "model", "parts": [{"text": "Listo, revisa el cambio y dale Confirmar."}]},
        ])
        original = admin_assistant.generate_content
        admin_assistant.generate_content = lambda *args: next(replies)
        try:
            answer = admin_assistant.generate_admin_reply(
                [{"role": "user", "text": "cámbiame el precio de Cali a 85 mil"}], self.company, BOLIVARIANO
            )
        finally:
            admin_assistant.generate_content = original
        self.assertEqual(answer["actions"], [{
            "summary": "Cambiar a $85.000 el precio de las 4 salidas de EXPRESO BOLIVARIANO a Cali",
            "path": f"/admin/routes/{CALI_ROUTE}/price", "body": {"price": 85000},
        }])
        route = next(r for r in admin.list_routes(BOLIVARIANO) if r["id"] == CALI_ROUTE)
        self.assertNotIn(85000, {d["price"] for d in route["departures"]})   # nothing changed yet

    def test_assistant_respects_the_company_scope_and_ranges(self):
        from ai.admin_assistant import AdminTools
        tools = AdminTools(CONTINENTAL)
        self.assertIn("error", tools.run("propose_route_price", {"route_id": CALI_ROUTE, "price": 85000}))
        self.assertIn("error", tools.run("propose_company_settings", {"company_id": CONTINENTAL,
                                                                      "reservation_minutes": 2}))
        proposal = tools.run("propose_company_settings", {"company_id": CONTINENTAL, "reservation_minutes": 8})
        self.assertIn("8 minutos para pagar", proposal["proposal"])
        self.assertEqual(tools.actions[0]["body"], {"reservation_minutes": 8})


    # ---------------- Editing everything ----------------

    def reserve(self, schedule_id=CALI_SCHEDULE_ID, seat=1):
        return purchases.reserve_seats(3, schedule_id, self.tomorrow,
                                       [{"seat": seat, "name": "Ana Pérez", "document": "1085123456"}])

    def test_texts_and_rules_change_from_the_panel(self):
        from services import settings
        settings.clear_cache()
        self.assertEqual(settings.get_setting("max_pending_purchases"), 2)
        settings.update_settings({"max_pending_purchases": 1, "home_title": "  Viaja con nosotros  "})
        self.assertEqual(settings.public_settings()["home_title"], "Viaja con nosotros")
        self.assertNotIn("ai_extra_instructions", settings.public_settings())
        self.reserve()
        with self.assertRaises(purchases.PurchaseError) as context:
            self.reserve(20)
        self.assertIn("1 compra sin pagar", context.exception.message)
        for bad in ({"max_pending_purchases": 0}, {"home_title": ""}, {"nope": 1}, {"sales_window_days": "9"}):
            with self.assertRaises(settings.SettingError):
                settings.update_settings(bad)
        settings.update_settings({"max_pending_purchases": 2})
        settings.clear_cache()

    def test_sales_window_follows_the_setting(self):
        from services import settings
        from services.dates import InvalidDateError, parse_travel_date
        settings.update_settings({"sales_window_days": 3})
        try:
            with self.assertRaises(InvalidDateError):
                parse_travel_date((today_in_colombia() + timedelta(days=4)).isoformat())
            parse_travel_date((today_in_colombia() + timedelta(days=3)).isoformat())
        finally:
            settings.update_settings({"sales_window_days": 60})

    def test_rename_company_destination_route_and_document(self):
        admin.rename_company(BOLIVARIANO, "bolivariano express")
        self.assertIn("BOLIVARIANO EXPRESS", [c["name"] for c in admin.list_companies()])
        with self.assertRaises(admin.AdminError):
            admin.rename_company(BOLIVARIANO, "TRANSIPIALES")
        cali = next(d for d in admin.list_destinations() if d["name"] == "Cali")
        admin.rename_destination(cali["id"], "Santiago de Cali")
        self.assertTrue(any(r["destination"] == "Santiago de Cali" for r in admin.list_routes()))
        admin.update_route(BOLIVARIANO, CALI_ROUTE, 600)
        with self.assertRaises(admin.AdminError):
            admin.update_route(CONTINENTAL, CALI_ROUTE, 600)
        admin.update_document_type("PA", name="Pasaporte extranjero", max_length=9)
        self.assertEqual(next(t for t in admin.list_document_types() if t["code"] == "PA")["max_length"], 9)

    def test_bus_capacity_and_departure_time(self):
        bus_id = admin.list_buses(BOLIVARIANO)[0]["id"]
        admin.update_bus(BOLIVARIANO, bus_id, capacity=44)
        self.assertEqual(len(purchases.get_seat_map(CALI_SCHEDULE_ID, self.tomorrow)["seats"]), 44)
        self.reserve(seat=43)
        with self.assertRaises(admin.AdminError):
            admin.update_bus(None, bus_id, capacity=40)        # seat 43 is held
        admin.update_bus(None, bus_id, plate="EXB-999", capacity=43)
        with self.assertRaises(admin.AdminError):
            admin.change_departure_time(None, CALI_SCHEDULE_ID, "19:00")   # it has a traveller
        moved = admin.change_departure_time(BOLIVARIANO, 20, "6:05")
        self.assertEqual(moved["departure_time"], "06:05")
        with self.assertRaises(admin.AdminError):
            admin.change_departure_time(BOLIVARIANO, 21, "06:05")         # same route, same hour

    def test_staff_cancels_and_refunds_purchases(self):
        pending = self.reserve(seat=5)
        found = admin.find_purchases(BOLIVARIANO, pending["booking_code"])
        self.assertEqual([p["payment_id"] for p in found], [pending["payment_id"]])
        self.assertEqual(admin.find_purchases(CONTINENTAL, pending["booking_code"]), [])
        admin.cancel_purchase_as_staff(BOLIVARIANO, pending["payment_id"])
        self.assertEqual(admin.find_purchases(None, "1085123456")[0]["status"], "CANCELLED")

        paid = self.reserve(seat=6)
        purchases.mark_as_paying(3, paid["payment_id"], "cs_test_paid", paid["expires_at"])
        purchases.confirm_payment(paid["payment_id"])
        with self.assertRaises(admin.AdminError):
            admin.cancel_purchase_as_staff(None, paid["payment_id"])      # paid: must be refunded
        refunded = []
        admin.refund_purchase_as_staff(None, paid["payment_id"], refunded.append)
        self.assertEqual(refunded, ["cs_test_paid"])
        self.assertEqual(purchases.confirm_payment(paid["payment_id"]), "CANCELLED")  # a repeated webhook
        self.reserve(seat=6)                                                       # the seat is free again


if __name__ == "__main__":
    unittest.main()
