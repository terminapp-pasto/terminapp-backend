"""What the terminal admin and the bus companies can manage.

Every function receives `company_scope`:
- None for the admin, who sees and changes every company.
- The company id for a company user, who only sees and changes its own company.
Asking for something of another company answers 404, as if it did not exist.
"""

import re
import psycopg

from services.catalog import read_document_types
from services.database import connect
from services.dates import today_in_colombia
from services.purchases import (
    DEFAULT_RESERVATION_MINUTES, MAX_SEATS_PER_PURCHASE, SEATS_PER_PURCHASE_LIMIT, _expire_old_reservations,
)
from services.users import ROLE_ADMIN, ROLE_COMPANY, ROLES
from services.validation import DOCUMENT_TYPE_CODE_PATTERN, normalize_spaces

ORIGIN = "Pasto"
MIN_RESERVATION_MINUTES = 5
MAX_RESERVATION_MINUTES = 30
MIN_PRICE = 1_000
MAX_PRICE = 2_000_000
MIN_DURATION = 10
MAX_DURATION = 4_000          # about 66 hours: Pasto to the Caribbean coast takes around 33
MIN_CAPACITY = 10
MAX_CAPACITY = 60
PLATE_PATTERN = re.compile(r"^[A-Z]{3}-?\d{3}$")
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
PLACE_PATTERN = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]{2,39}$")
COMPANY_PATTERN = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .&'-]{2,59}$")
DOCUMENT_NAME_PATTERN = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,39}$")
USER_SEARCH_LIMIT = 20


class AdminError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ------------------------------------------------------------------
# Checks
# ------------------------------------------------------------------

def _check_range(value, low, high, message):
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise AdminError(message)
    return value


def check_price(price):
    return _check_range(price, MIN_PRICE, MAX_PRICE, f"El precio debe estar entre ${MIN_PRICE:,} y ${MAX_PRICE:,}".replace(",", "."))


def check_reservation_minutes(minutes):
    return _check_range(
        minutes, MIN_RESERVATION_MINUTES, MAX_RESERVATION_MINUTES,
        f"El tiempo para pagar debe estar entre {MIN_RESERVATION_MINUTES} y {MAX_RESERVATION_MINUTES} minutos",
    )


def check_max_seats(seats):
    return _check_range(seats, 1, SEATS_PER_PURCHASE_LIMIT,
                        f"Las sillas por compra deben estar entre 1 y {SEATS_PER_PURCHASE_LIMIT}")


def check_time(text):
    text = str(text).strip()
    if len(text) == 4 and text[1] == ":":
        text = "0" + text  # 6:30 -> 06:30
    if not TIME_PATTERN.match(text):
        raise AdminError("La hora debe tener el formato HH:MM, por ejemplo 06:30 o 21:00")
    return text


def check_plate(plate):
    plate = str(plate).strip().upper().replace(" ", "")
    if not PLATE_PATTERN.match(plate):
        raise AdminError("La placa debe tener 3 letras y 3 números, por ejemplo TRP-101")
    return plate if "-" in plate else f"{plate[:3]}-{plate[3:]}"


def _own(company_scope, company_id):
    """A company user can only touch its own company."""
    if company_scope is not None and company_id != company_scope:
        raise AdminError("No encontramos esa empresa", 404)


# ------------------------------------------------------------------
# Companies and their settings
# ------------------------------------------------------------------

COMPANIES_QUERY = """
    SELECT c.id, c.name, c.max_seats_per_purchase, c.reservation_minutes,
           (SELECT COUNT(*) FROM buses b WHERE b.company_id = c.id),
           (SELECT COUNT(*) FROM routes r WHERE r.company_id = c.id),
           (SELECT COUNT(*) FROM schedules s JOIN routes r ON r.id = s.route_id
            WHERE r.company_id = c.id AND s.active)
    FROM companies c
    WHERE %(scope)s::int IS NULL OR c.id = %(scope)s::int
    ORDER BY c.name;
"""


def list_companies(company_scope=None):
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(COMPANIES_QUERY, {"scope": company_scope})
        return [
            {"id": row[0], "name": row[1], "max_seats_per_purchase": row[2], "reservation_minutes": row[3],
             "buses": row[4], "routes": row[5], "departures": row[6]}
            for row in cursor.fetchall()
        ]


def create_company(name, max_seats=MAX_SEATS_PER_PURCHASE, reservation_minutes=DEFAULT_RESERVATION_MINUTES):
    """Admin only. The name is saved in capitals, like the terminal's directory."""
    name = normalize_spaces(name).upper()
    if not COMPANY_PATTERN.match(name):
        raise AdminError("El nombre de la empresa debe tener de 3 a 60 letras o números")
    check_max_seats(max_seats)
    check_reservation_minutes(reservation_minutes)
    try:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO companies (name, max_seats_per_purchase, reservation_minutes)
                   VALUES (%s, %s, %s) RETURNING id;""",
                (name, max_seats, reservation_minutes),
            )
            company_id = cursor.fetchone()[0]
    except psycopg.errors.UniqueViolation:
        raise AdminError("Ya existe una empresa con ese nombre", 409)
    return {"id": company_id, "name": name, "max_seats_per_purchase": max_seats,
            "reservation_minutes": reservation_minutes}


def update_company_settings(company_scope, company_id, max_seats=None, reservation_minutes=None):
    """Seats per purchase and minutes to pay. Only affects new purchases."""
    _own(company_scope, company_id)
    if max_seats is None and reservation_minutes is None:
        raise AdminError("No hay nada que cambiar")
    if max_seats is not None:
        check_max_seats(max_seats)
    if reservation_minutes is not None:
        check_reservation_minutes(reservation_minutes)
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """UPDATE companies
               SET max_seats_per_purchase = COALESCE(%s, max_seats_per_purchase),
                   reservation_minutes = COALESCE(%s, reservation_minutes)
               WHERE id = %s RETURNING id, name, max_seats_per_purchase, reservation_minutes;""",
            (max_seats, reservation_minutes, company_id),
        )
        row = cursor.fetchone()
    if row is None:
        raise AdminError("No encontramos esa empresa", 404)
    return {"id": row[0], "name": row[1], "max_seats_per_purchase": row[2], "reservation_minutes": row[3]}


# ------------------------------------------------------------------
# Buses
# ------------------------------------------------------------------

def list_buses(company_scope=None):
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT b.id, b.plate, b.capacity, c.id, c.name,
                      (SELECT COUNT(*) FROM schedules s WHERE s.bus_id = b.id AND s.active)
               FROM buses b JOIN companies c ON c.id = b.company_id
               WHERE %(scope)s::int IS NULL OR c.id = %(scope)s::int
               ORDER BY c.name, b.plate;""",
            {"scope": company_scope},
        )
        return [
            {"id": row[0], "plate": row[1], "capacity": row[2], "company_id": row[3], "company": row[4],
             "departures": row[5]}
            for row in cursor.fetchall()
        ]


def create_bus(company_scope, company_id, plate, capacity):
    """Adds a bus and its numbered seats (1 to capacity)."""
    _own(company_scope, company_id)
    plate = check_plate(plate)
    _check_range(capacity, MIN_CAPACITY, MAX_CAPACITY,
                 f"La capacidad debe estar entre {MIN_CAPACITY} y {MAX_CAPACITY} sillas")
    try:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM companies WHERE id = %s;", (company_id,))
            if cursor.fetchone() is None:
                raise AdminError("No encontramos esa empresa", 404)
            cursor.execute(
                "INSERT INTO buses (company_id, plate, capacity) VALUES (%s, %s, %s) RETURNING id;",
                (company_id, plate, capacity),
            )
            bus_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO seats (bus_id, number) SELECT %s, n FROM generate_series(1, %s) AS n;",
                (bus_id, capacity),
            )
    except psycopg.errors.UniqueViolation:
        raise AdminError("Ya existe un bus con esa placa", 409)
    return {"id": bus_id, "plate": plate, "capacity": capacity, "company_id": company_id}


# ------------------------------------------------------------------
# Destinations, routes and departures
# ------------------------------------------------------------------

def list_destinations():
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id, name FROM destinations ORDER BY name;")
        return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]


def _find_or_create_destination(cursor, name, can_create):
    name = normalize_spaces(name)
    if not PLACE_PATTERN.match(name):
        raise AdminError("El destino debe tener de 3 a 40 letras")
    cursor.execute("SELECT id, name FROM destinations WHERE lower(name) = lower(%s);", (name,))
    row = cursor.fetchone()
    if row is not None:
        return row
    if not can_create:
        raise AdminError(f"{name} todavía no es un destino de la terminal. Pídele al administrador que lo cree", 404)
    cursor.execute("INSERT INTO destinations (name) VALUES (%s) RETURNING id, name;", (name[0].upper() + name[1:],))
    return cursor.fetchone()


ROUTES_QUERY = """
    SELECT r.id, c.id, c.name, o.name, d.name, r.duration_min,
           s.id, s.departure_time, s.price, s.active, b.id, b.plate, b.capacity
    FROM routes r
    JOIN companies c ON c.id = r.company_id
    JOIN destinations o ON o.id = r.origin_id
    JOIN destinations d ON d.id = r.destination_id
    LEFT JOIN schedules s ON s.route_id = r.id
    LEFT JOIN buses b ON b.id = s.bus_id
    WHERE %(scope)s::int IS NULL OR c.id = %(scope)s::int
    ORDER BY d.name, c.name, r.id, s.departure_time;
"""


def list_routes(company_scope=None):
    """Every route with its departures (price, bus and whether it is on sale)."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(ROUTES_QUERY, {"scope": company_scope})
        rows = cursor.fetchall()
    routes = []
    by_id = {}
    for (route_id, company_id, company, origin, destination, duration, schedule_id, departure_time, price,
         active, bus_id, plate, capacity) in rows:
        route = by_id.get(route_id)
        if route is None:
            route = {"id": route_id, "company_id": company_id, "company": company, "origin": origin,
                     "destination": destination, "duration_min": duration, "departures": []}
            by_id[route_id] = route
            routes.append(route)
        if schedule_id is not None:
            route["departures"].append({
                "id": schedule_id, "departure_time": departure_time.strftime("%H:%M"), "price": price,
                "active": active, "bus_id": bus_id, "plate": plate, "capacity": capacity,
            })
    return routes


def _route_company(cursor, route_id):
    cursor.execute("SELECT company_id FROM routes WHERE id = %s;", (route_id,))
    row = cursor.fetchone()
    if row is None:
        raise AdminError("No encontramos esa ruta", 404)
    return row[0]


def create_route(company_scope, company_id, destination, duration_min):
    """A new route from Pasto. Only the admin can add a destination that does not exist yet."""
    _own(company_scope, company_id)
    _check_range(duration_min, MIN_DURATION, MAX_DURATION,
                 f"La duración debe estar entre {MIN_DURATION} y {MAX_DURATION} minutos")
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM companies WHERE id = %s;", (company_id,))
        if cursor.fetchone() is None:
            raise AdminError("No encontramos esa empresa", 404)
        origin_id, _ = _find_or_create_destination(cursor, ORIGIN, False)
        destination_id, destination_name = _find_or_create_destination(cursor, destination, company_scope is None)
        if destination_id == origin_id:
            raise AdminError("El destino no puede ser Pasto")
        cursor.execute(
            "SELECT id FROM routes WHERE company_id = %s AND origin_id = %s AND destination_id = %s;",
            (company_id, origin_id, destination_id),
        )
        if cursor.fetchone() is not None:
            raise AdminError(f"Esa empresa ya tiene una ruta a {destination_name}", 409)
        cursor.execute(
            "INSERT INTO routes (company_id, origin_id, destination_id, duration_min) VALUES (%s, %s, %s, %s) "
            "RETURNING id;",
            (company_id, origin_id, destination_id, duration_min),
        )
        route_id = cursor.fetchone()[0]
    return {"id": route_id, "company_id": company_id, "origin": ORIGIN, "destination": destination_name,
            "duration_min": duration_min}


def _check_bus(cursor, bus_id, company_id):
    cursor.execute("SELECT capacity FROM buses WHERE id = %s AND company_id = %s;", (bus_id, company_id))
    row = cursor.fetchone()
    if row is None:
        raise AdminError("Ese bus no es de la empresa de esta ruta", 404)
    return row[0]


def create_departure(company_scope, route_id, departure_time, price, bus_id):
    departure_time = check_time(departure_time)
    check_price(price)
    with connect() as connection, connection.cursor() as cursor:
        company_id = _route_company(cursor, route_id)
        _own(company_scope, company_id)
        capacity = _check_bus(cursor, bus_id, company_id)
        cursor.execute(
            "SELECT 1 FROM schedules WHERE route_id = %s AND departure_time = %s;", (route_id, departure_time)
        )
        if cursor.fetchone() is not None:
            raise AdminError(f"Esa ruta ya tiene una salida a las {departure_time}", 409)
        cursor.execute(
            """INSERT INTO schedules (route_id, departure_time, price, seats, bus_id)
               VALUES (%s, %s, %s, %s, %s) RETURNING id;""",
            (route_id, departure_time, price, capacity, bus_id),
        )
        schedule_id = cursor.fetchone()[0]
    return {"id": schedule_id, "route_id": route_id, "departure_time": departure_time, "price": price,
            "bus_id": bus_id, "active": True}


def update_departure(company_scope, schedule_id, price=None, bus_id=None, active=None):
    """Changes the price, the bus or whether a departure is on sale.
    Purchases already made keep the price they were made with. The bus can only change
    while nobody holds a seat on a future trip, because seats belong to a bus."""
    if price is None and bus_id is None and active is None:
        raise AdminError("No hay nada que cambiar")
    if price is not None:
        check_price(price)
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT r.company_id, s.bus_id FROM schedules s JOIN routes r ON r.id = s.route_id WHERE s.id = %s;",
            (schedule_id,),
        )
        row = cursor.fetchone()
        if row is None:
            raise AdminError("No encontramos esa salida", 404)
        company_id, current_bus = row
        _own(company_scope, company_id)
        capacity = None
        if bus_id is not None and bus_id != current_bus:
            capacity = _check_bus(cursor, bus_id, company_id)
            _expire_old_reservations(cursor)
            cursor.execute(
                """SELECT COUNT(*) FROM tickets WHERE schedule_id = %s AND travel_date >= %s
                   AND status IN ('RESERVED', 'PAYING', 'PAID');""",
                (schedule_id, today_in_colombia()),
            )
            if cursor.fetchone()[0] > 0:
                raise AdminError(
                    "Esta salida ya tiene pasajes vendidos o apartados, por eso no se le puede cambiar el bus", 409
                )
        cursor.execute(
            """UPDATE schedules
               SET price = COALESCE(%s, price), bus_id = COALESCE(%s, bus_id), seats = COALESCE(%s, seats),
                   active = COALESCE(%s, active)
               WHERE id = %s
               RETURNING id, route_id, departure_time, price, bus_id, active;""",
            (price, bus_id, capacity, active, schedule_id),
        )
        row = cursor.fetchone()
    return {"id": row[0], "route_id": row[1], "departure_time": row[2].strftime("%H:%M"), "price": row[3],
            "bus_id": row[4], "active": row[5]}


def set_route_price(company_scope, route_id, price):
    """Sets the same price on every departure of a route ("cámbiame el precio de Cali")."""
    check_price(price)
    with connect() as connection, connection.cursor() as cursor:
        _own(company_scope, _route_company(cursor, route_id))
        cursor.execute("UPDATE schedules SET price = %s WHERE route_id = %s;", (price, route_id))
        changed = cursor.rowcount
    return {"route_id": route_id, "price": price, "departures_changed": changed}


# ------------------------------------------------------------------
# Document types (admin only)
# ------------------------------------------------------------------

def list_document_types():
    with connect() as connection, connection.cursor() as cursor:
        return read_document_types(cursor, only_active=False)


def create_document_type(code, name, min_length, max_length, allows_letters):
    code = str(code).strip().upper()
    name = normalize_spaces(name)
    if not DOCUMENT_TYPE_CODE_PATTERN.match(code):
        raise AdminError("El código debe tener 2 letras, por ejemplo PT")
    if not DOCUMENT_NAME_PATTERN.match(name):
        raise AdminError("El nombre debe tener de 3 a 40 letras")
    _check_range(min_length, 3, 12, "La longitud mínima debe estar entre 3 y 12")
    _check_range(max_length, min_length, 12, "La longitud máxima debe estar entre la mínima y 12")
    try:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO document_types (code, name, min_length, max_length, allows_letters)
                   VALUES (%s, %s, %s, %s, %s);""",
                (code, name, min_length, max_length, bool(allows_letters)),
            )
    except psycopg.errors.UniqueViolation:
        raise AdminError("Ya existe un tipo de documento con ese código", 409)
    return {"code": code, "name": name, "min_length": min_length, "max_length": max_length,
            "allows_letters": bool(allows_letters), "active": True}


def set_document_type_active(code, active):
    with connect() as connection, connection.cursor() as cursor:
        if not active:
            cursor.execute("SELECT COUNT(*) FROM document_types WHERE active AND code <> %s;", (code,))
            if cursor.fetchone()[0] == 0:
                raise AdminError("Debe quedar al menos un tipo de documento activo")
        cursor.execute("UPDATE document_types SET active = %s WHERE code = %s RETURNING code;", (active, code))
        if cursor.fetchone() is None:
            raise AdminError("No encontramos ese tipo de documento", 404)
    return {"code": code, "active": active}


# ------------------------------------------------------------------
# Users and roles (admin only)
# ------------------------------------------------------------------

def find_users(text=""):
    text = normalize_spaces(text)[:100]
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """SELECT u.id, u.name, u.email, u.role, u.company_id, c.name
               FROM users u LEFT JOIN companies c ON c.id = u.company_id
               WHERE %(text)s = '' OR u.email ILIKE %(pattern)s OR u.name ILIKE %(pattern)s
               ORDER BY (u.role = 'user'), u.name LIMIT %(limit)s;""",
            {"text": text, "pattern": f"%{text}%", "limit": USER_SEARCH_LIMIT},
        )
        return [
            {"id": row[0], "name": row[1], "email": row[2], "role": row[3], "company_id": row[4], "company": row[5]}
            for row in cursor.fetchall()
        ]


def set_user_role(admin_id, user_id, role, company_id=None):
    """Makes someone a traveller, an employee of one company, or an admin."""
    if role not in ROLES:
        raise AdminError("El rol debe ser user, company o admin")
    if role == ROLE_COMPANY and company_id is None:
        raise AdminError("Elige la empresa de este usuario")
    if role != ROLE_COMPANY:
        company_id = None
    if user_id == admin_id and role != ROLE_ADMIN:
        raise AdminError("No puedes quitarte a ti mismo el rol de administrador")
    with connect() as connection, connection.cursor() as cursor:
        if company_id is not None:
            cursor.execute("SELECT 1 FROM companies WHERE id = %s;", (company_id,))
            if cursor.fetchone() is None:
                raise AdminError("No encontramos esa empresa", 404)
        cursor.execute(
            "UPDATE users SET role = %s, company_id = %s WHERE id = %s RETURNING id, name, email;",
            (role, company_id, user_id),
        )
        row = cursor.fetchone()
    if row is None:
        raise AdminError("No encontramos ese usuario", 404)
    return {"id": row[0], "name": row[1], "email": row[2], "role": role, "company_id": company_id}


# ------------------------------------------------------------------
# Bus occupancy
# ------------------------------------------------------------------

OCCUPANCY_QUERY = """
    SELECT s.id, c.name, d.name, s.departure_time, s.price, b.plate, b.capacity,
           COUNT(t.id) FILTER (WHERE t.status = 'PAID'),
           COUNT(t.id) FILTER (WHERE t.status IN ('RESERVED', 'PAYING')),
           COALESCE(SUM(pm.amount / NULLIF(pt.tickets, 0)) FILTER (WHERE t.status = 'PAID'), 0)
    FROM schedules s
    JOIN routes r ON r.id = s.route_id
    JOIN companies c ON c.id = r.company_id
    JOIN destinations d ON d.id = r.destination_id
    JOIN buses b ON b.id = s.bus_id
    LEFT JOIN tickets t ON t.schedule_id = s.id AND t.travel_date = %(date)s
    LEFT JOIN payments pm ON pm.id = t.payment_id
    LEFT JOIN (SELECT payment_id, COUNT(*) AS tickets FROM tickets GROUP BY payment_id) pt
           ON pt.payment_id = t.payment_id
    WHERE s.active AND (%(scope)s::int IS NULL OR c.id = %(scope)s::int)
    GROUP BY s.id, c.name, d.name, s.departure_time, s.price, b.plate, b.capacity
    ORDER BY s.departure_time, d.name, c.name;
"""


def occupancy(company_scope, travel_date):
    """Every departure of a day with how full its bus is: sold, held and free seats."""
    with connect() as connection, connection.cursor() as cursor:
        _expire_old_reservations(cursor)
        cursor.execute(OCCUPANCY_QUERY, {"date": travel_date, "scope": company_scope})
        rows = cursor.fetchall()
    departures = []
    for schedule_id, company, destination, departure_time, price, plate, capacity, sold, held, revenue in rows:
        departures.append({
            "schedule_id": schedule_id, "company": company, "destination": destination,
            "departure_time": departure_time.strftime("%H:%M"), "price": price, "plate": plate,
            "capacity": capacity, "sold": sold, "held": held, "free": capacity - sold - held,
            "occupancy_percent": round((sold + held) * 100 / capacity) if capacity else 0,
            "revenue": int(revenue),
        })
    totals = {
        "departures": len(departures),
        "seats": sum(d["capacity"] for d in departures),
        "sold": sum(d["sold"] for d in departures),
        "held": sum(d["held"] for d in departures),
        "revenue": sum(d["revenue"] for d in departures),
    }
    totals["occupancy_percent"] = round((totals["sold"] + totals["held"]) * 100 / totals["seats"]) if totals["seats"] else 0
    return {"date": travel_date.isoformat(), "totals": totals, "departures": departures}
