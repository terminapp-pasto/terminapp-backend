"""Ticket purchase: seats, reservations, expirations and history.

The 5 purchase structures work together here:
- HashTable: seat map of a departure (number -> status), O(1) lookups.
- Stack: undo log when several seats are reserved and one of them fails.
- Queue: pending reservations in arrival order, to expire the old ones.
- StateMachine: decides which status changes are valid for a ticket.
- DoublyLinkedList: the user's purchase history, walkable in both directions.

Concurrency (two people asking for the last seat at the same time):
1. Reserving locks the departure row (SELECT ... FOR UPDATE). PostgreSQL queues
   (FIFO) the other reservations for that departure: the second one waits for
   the first to finish and then sees the seat already taken.
2. As a safety net, the unique index unique_seat_per_trip prevents two live
   tickets from having the same seat on the same departure and date.
"""

import secrets
from datetime import datetime, timedelta, timezone

import psycopg

from services.database import connect
from services.dates import COLOMBIA_TIMEZONE, SALES_WINDOW_DAYS, now_in_colombia
from services.validation import (
    DEFAULT_DOCUMENT_TYPE, DOCUMENT_TYPE_RULE, NAME_RULE, document_rule, is_valid_document_of_type,
    is_valid_document_type, is_valid_name, normalize_document, normalize_spaces,
)
from structs.doubly_linked_list import DoublyLinkedList
from structs.hash_table import HashTable
from structs.queue import Queue
from structs.stack import Stack
from structs.state_machine import (
    CANCEL, CONFIRM_PAYMENT, EXPIRE, PAID, PAYING, RECOVER_PAYMENT, RESERVE, RESERVED, SELECTING,
    START_PAYMENT, TransitionError, purchase_state_machine,
)

RESERVATION_MINUTES = 15       # time to open the payment after reserving
PAYMENT_WINDOW_MINUTES = 31    # time to finish paying once the payment is open (Stripe's minimum is 30)
MAX_SEATS_PER_PURCHASE = 5
MAX_PENDING_PURCHASES = 2      # unpaid purchases a user may hold at the same time, across all trips

FREE = "FREE"
TAKEN = "TAKEN"
ACTIVE_STATUSES = (RESERVED, PAYING, PAID)
PENDING_STATUSES = (RESERVED, PAYING)

NEWEST_FIRST = "newest"
OLDEST_FIRST = "oldest"

PAYMENT_PENDING = "PENDING"
PAYMENT_PAID = "PAID"
PAYMENT_CANCELLED = "CANCELLED"
PAYMENT_EXPIRED = "EXPIRED"
PAYMENT_REFUNDED = "REFUNDED"

BOOKING_CODE_LENGTH = 6
# Letters and digits that cannot be confused when read aloud or on paper (no O/0, I/1)
BOOKING_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# Answers of the Stripe check made before expiring an open payment
SESSION_PAID = "paid"
SESSION_NOT_PAID = "not_paid"
SESSION_UNKNOWN = "unknown"


class PurchaseError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SeatsLostError(Exception):
    """A payment arrived after its reservation expired and the seats were sold to someone else.
    The caller must refund it."""

    def __init__(self, payment_id, stripe_session_id):
        super().__init__(f"Payment {payment_id} arrived after its seats were sold")
        self.payment_id = payment_id
        self.stripe_session_id = stripe_session_id


def _default_session_checker(stripe_session_id):
    # imported here so the purchase logic can be tested without Stripe
    from payments.stripe_client import close_session_and_check
    return close_session_and_check(stripe_session_id)


# Closes a Stripe session and says whether it was paid. Tests replace it with a fake.
stripe_session_checker = _default_session_checker


# ------------------------------------------------------------------
# Pure logic with the structures (does not touch the database)
# ------------------------------------------------------------------

def build_seat_map(capacity, taken_numbers):
    """Builds the hash table with every seat FREE and marks the taken ones."""
    seat_map = HashTable(capacity * 2)
    for number in range(1, capacity + 1):
        seat_map.put(number, FREE)
    for number in taken_numbers:
        seat_map.put(number, TAKEN)
    return seat_map


def seats_in_order(seat_map, capacity):
    """Turns the map into the sorted list sent to the frontend."""
    return [{"number": n, "status": seat_map.get(n)} for n in range(1, capacity + 1)]


def hold_seats(seat_map, numbers):
    """Holds each requested seat. If one is already taken, it undoes the previous ones
    with the stack (in reverse order) and returns that number; if all goes well, None."""
    undo_log = Stack()
    for number in numbers:
        if seat_map.get(number) != FREE:
            while not undo_log.is_empty():
                seat_map.put(undo_log.pop(), FREE)
            return number
        seat_map.put(number, RESERVED)
        undo_log.push(number)
    return None


def find_expired(pending_tickets, now):
    """Receives (id, status, deadline) sorted by deadline, earliest first, and returns
    the ones whose deadline has passed. The queue keeps that order: it only looks at
    the front and stops at the first one that is still on time."""
    queue = Queue()
    for ticket in pending_tickets:
        queue.enqueue(ticket)

    expired = []
    while not queue.is_empty() and queue.peek()[2] < now:
        ticket = queue.dequeue()
        expired.append(ticket)
    return expired


def purchase_history(purchases, order=NEWEST_FIRST):
    """Builds the doubly linked list (newest at the head) and walks it in the requested direction."""
    history = DoublyLinkedList()
    for purchase in purchases:  # they arrive from newest to oldest
        history.append(purchase)
    result = []
    if order == OLDEST_FIRST:
        history.traverse_backward(result.append)
    else:
        history.traverse_forward(result.append)
    return result


def next_status(current_status, event):
    """Asks the state machine for the next status; raises PurchaseError if not allowed."""
    try:
        return purchase_state_machine(current_status).trigger(event)
    except TransitionError as error:
        raise PurchaseError(str(error), 409)


def expiration_time(status, created_at, payment_expires_at=None):
    """Colombian time until which an unpaid purchase is held (None if not applicable).
    A reservation lasts RESERVATION_MINUTES; an open payment lasts as long as its Stripe session."""
    if status == RESERVED:
        deadline = created_at + timedelta(minutes=RESERVATION_MINUTES)
    elif status == PAYING:
        deadline = payment_expires_at or created_at + timedelta(minutes=RESERVATION_MINUTES + PAYMENT_WINDOW_MINUTES)
    else:
        return None
    return deadline.astimezone(COLOMBIA_TIMEZONE)


def generate_booking_code():
    """Random code like "K7M2QX": 32^6 ≈ 1,000 million options, so it cannot be guessed."""
    return "".join(secrets.choice(BOOKING_CODE_ALPHABET) for _ in range(BOOKING_CODE_LENGTH))


def _new_booking_code(cursor):
    """A booking code that no other purchase has."""
    while True:
        code = generate_booking_code()
        cursor.execute("SELECT 1 FROM payments WHERE booking_code = %s;", (code,))
        if cursor.fetchone() is None:
            return code


def clean_passengers(passengers):
    """Validates the passengers (one per seat) and returns [(seat, name, document_type, document)].
    document_type is optional and defaults to CC (national ID)."""
    if not passengers:
        raise PurchaseError("Elige al menos un asiento")
    if len(passengers) > MAX_SEATS_PER_PURCHASE:
        raise PurchaseError(f"Puedes comprar máximo {MAX_SEATS_PER_PURCHASE} asientos por compra")

    cleaned = []
    seen_seats = HashTable()
    for position, passenger in enumerate(passengers, start=1):
        seat = passenger["seat"]
        name = normalize_spaces(passenger["name"])
        document_type = str(passenger.get("document_type") or DEFAULT_DOCUMENT_TYPE).upper()
        document = normalize_document(passenger["document"])
        if seen_seats.contains(seat):
            raise PurchaseError(f"El asiento {seat} está repetido")
        seen_seats.put(seat, True)
        if not is_valid_name(name):
            raise PurchaseError(f"Pasajero {position}: {NAME_RULE}")
        if not is_valid_document_type(document_type):
            raise PurchaseError(f"Pasajero {position}: {DOCUMENT_TYPE_RULE}")
        if not is_valid_document_of_type(document, document_type):
            raise PurchaseError(f"Pasajero {position}: {document_rule(document_type)}")
        cleaned.append((seat, name, document_type, document))
    return cleaned


# ------------------------------------------------------------------
# Queries
# ------------------------------------------------------------------

DEPARTURE_QUERY = """
    SELECT s.id, s.departure_time, s.price, c.name, o.name, d.name,
           r.duration_min, b.id, b.capacity, b.plate
    FROM schedules s
    JOIN routes r ON r.id = s.route_id
    JOIN companies c ON c.id = r.company_id
    JOIN destinations o ON o.id = r.origin_id
    JOIN destinations d ON d.id = r.destination_id
    JOIN buses b ON b.company_id = r.company_id
    WHERE s.id = %s
    LIMIT 1;
"""

TAKEN_SEATS_QUERY = """
    SELECT st.number
    FROM tickets t
    JOIN seats st ON st.id = t.seat_id
    WHERE t.schedule_id = %s AND t.travel_date = %s AND t.status IN ('RESERVED', 'PAYING', 'PAID');
"""


PENDING_DEADLINES_QUERY = f"""
    SELECT t.payment_id, t.status, deadline, pm.stripe_session_id
    FROM (
        SELECT t.payment_id, t.status,
               CASE WHEN t.status = 'RESERVED' THEN MIN(t.created_at) + INTERVAL '{RESERVATION_MINUTES} minutes'
                    ELSE COALESCE(pm.expires_at,
                                  MIN(t.created_at) + INTERVAL '{RESERVATION_MINUTES + PAYMENT_WINDOW_MINUTES} minutes')
               END AS deadline
        FROM tickets t JOIN payments pm ON pm.id = t.payment_id
        WHERE t.status IN ('RESERVED', 'PAYING')
        GROUP BY t.payment_id, t.status, pm.expires_at
    ) t
    JOIN payments pm ON pm.id = t.payment_id
    ORDER BY deadline;
"""


def _expire_old_reservations(cursor):
    """Expires the purchases whose time ran out. Before expiring an open payment it closes
    the Stripe session and asks whether it was paid, so nobody is charged without a ticket."""
    cursor.execute(PENDING_DEADLINES_QUERY)
    for payment_id, status, _, stripe_session_id in find_expired(cursor.fetchall(), datetime.now(timezone.utc)):
        if status == PAYING and stripe_session_id:
            answer = stripe_session_checker(stripe_session_id)
            if answer == SESSION_PAID:
                new_status = next_status(status, CONFIRM_PAYMENT)
                cursor.execute("UPDATE tickets SET status = %s WHERE payment_id = %s;", (new_status, payment_id))
                cursor.execute("UPDATE payments SET status = 'PAID' WHERE id = %s;", (payment_id,))
                continue
            if answer == SESSION_UNKNOWN:
                continue  # Stripe did not answer: keep the seats and check again on the next request
        new_status = next_status(status, EXPIRE)
        cursor.execute("UPDATE tickets SET status = %s WHERE payment_id = %s;", (new_status, payment_id))
        cursor.execute("UPDATE payments SET status = 'EXPIRED' WHERE id = %s AND status = 'PENDING';", (payment_id,))


def _get_departure(cursor, schedule_id, lock=False):
    cursor.execute(DEPARTURE_QUERY, (schedule_id,))
    row = cursor.fetchone()
    if row is None:
        raise PurchaseError("Esa salida no existe", 404)
    if lock:
        # Queues the other reservations for this departure until this one finishes
        cursor.execute("SELECT id FROM schedules WHERE id = %s FOR UPDATE;", (schedule_id,))
    return {
        "schedule_id": row[0],
        "departure_time": row[1].strftime("%H:%M"),
        "price": row[2],
        "company": row[3],
        "origin": row[4],
        "destination": row[5],
        "duration_min": row[6],
        "bus_id": row[7],
        "capacity": row[8],
        "plate": row[9],
    }


def _check_travel_date(travel_date, departure):
    now = now_in_colombia()
    today = now.date()
    if travel_date < today:
        raise PurchaseError("No se pueden comprar pasajes para fechas pasadas")
    if travel_date > today + timedelta(days=SALES_WINDOW_DAYS):
        raise PurchaseError(f"Solo se venden pasajes hasta {SALES_WINDOW_DAYS} días adelante")
    if travel_date == today and departure["departure_time"] <= now.strftime("%H:%M"):
        raise PurchaseError("Ese bus ya salió hoy. Elige otra hora u otro día")


def get_seat_map(schedule_id, travel_date):
    with connect() as connection, connection.cursor() as cursor:
        _expire_old_reservations(cursor)
        departure = _get_departure(cursor, schedule_id)
        cursor.execute(TAKEN_SEATS_QUERY, (schedule_id, travel_date))
        seat_map = build_seat_map(departure["capacity"], (row[0] for row in cursor))
        seats = seats_in_order(seat_map, departure["capacity"])
        free_seats = sum(1 for seat in seats if seat["status"] == FREE)
        return {"departure": departure, "date": travel_date.isoformat(), "free_seats": free_seats, "seats": seats}


def _cancel_pending_purchases_for_trip(cursor, user_id, schedule_id, travel_date):
    """If the user already had an unpaid purchase for this same trip, cancels it so
    there are never two payments in progress. Returns the Stripe sessions to close."""
    cursor.execute(
        """SELECT DISTINCT t.payment_id, t.status, pm.stripe_session_id
           FROM tickets t
           JOIN passengers p ON p.id = t.passenger_id
           JOIN payments pm ON pm.id = t.payment_id
           WHERE p.user_id = %s AND t.schedule_id = %s AND t.travel_date = %s
             AND t.status IN ('RESERVED', 'PAYING');""",
        (user_id, schedule_id, travel_date),
    )
    stripe_sessions = []
    for payment_id, status, stripe_session_id in cursor.fetchall():
        new_status = next_status(status, CANCEL)
        cursor.execute("UPDATE tickets SET status = %s WHERE payment_id = %s;", (new_status, payment_id))
        cursor.execute("UPDATE payments SET status = 'CANCELLED' WHERE id = %s;", (payment_id,))
        if stripe_session_id:
            stripe_sessions.append(stripe_session_id)
    return stripe_sessions


def reserve_seats(user_id, schedule_id, travel_date, passengers):
    """Holds the seats (one passenger per seat) for RESERVATION_MINUTES minutes.
    passengers: list of {"seat", "name", "document"}."""
    cleaned = clean_passengers(passengers)
    numbers = [seat for seat, _, _, _ in cleaned]

    with connect() as connection, connection.cursor() as cursor:
        _expire_old_reservations(cursor)
        departure = _get_departure(cursor, schedule_id, lock=True)
        _check_travel_date(travel_date, departure)

        for number in numbers:
            if number < 1 or number > departure["capacity"]:
                raise PurchaseError(f"El asiento {number} no existe en este bus")

        replaced_sessions = _cancel_pending_purchases_for_trip(cursor, user_id, schedule_id, travel_date)

        cursor.execute(
            """SELECT COUNT(DISTINCT t.payment_id)
               FROM tickets t JOIN passengers p ON p.id = t.passenger_id
               WHERE p.user_id = %s AND t.status IN ('RESERVED', 'PAYING');""",
            (user_id,),
        )
        if cursor.fetchone()[0] >= MAX_PENDING_PURCHASES:
            raise PurchaseError(
                f"Ya tienes {MAX_PENDING_PURCHASES} compras sin pagar. Págalas o cancélalas en Mis viajes "
                "antes de apartar más asientos.",
                409,
            )

        cursor.execute(TAKEN_SEATS_QUERY, (schedule_id, travel_date))
        seat_map = build_seat_map(departure["capacity"], (row[0] for row in cursor))
        taken_number = hold_seats(seat_map, numbers)
        if taken_number is not None:
            raise PurchaseError(f"El asiento {taken_number} acaba de ser ocupado. Elige otro", 409)

        cursor.execute(
            "SELECT number, id FROM seats WHERE bus_id = %s AND number = ANY(%s);",
            (departure["bus_id"], numbers),
        )
        seat_ids = HashTable()
        for number, seat_id in cursor:
            seat_ids.put(number, seat_id)

        total = departure["price"] * len(numbers)
        booking_code = _new_booking_code(cursor)
        cursor.execute(
            "INSERT INTO payments (amount, status, booking_code) VALUES (%s, 'PENDING', %s) RETURNING id, created_at;",
            (total, booking_code),
        )
        payment_id, created_at = cursor.fetchone()

        status = next_status(SELECTING, RESERVE)
        try:
            for number, name, document_type, document in cleaned:
                cursor.execute(
                    """INSERT INTO passengers (user_id, name, document_type, document)
                       VALUES (%s, %s, %s, %s) RETURNING id;""",
                    (user_id, name, document_type, document),
                )
                passenger_id = cursor.fetchone()[0]
                cursor.execute(
                    """INSERT INTO tickets (schedule_id, travel_date, status, passenger_id, seat_id, payment_id)
                       VALUES (%s, %s, %s, %s, %s, %s);""",
                    (schedule_id, travel_date, status, passenger_id, seat_ids.get(number), payment_id),
                )
        except psycopg.errors.UniqueViolation:
            # someone else took the seat at the same instant: the unique index stopped it
            raise PurchaseError("Uno de los asientos acaba de ser ocupado. Elige otro", 409)

    return {
        "payment_id": payment_id,
        "booking_code": booking_code,
        "status": status,
        "departure": departure,
        "date": travel_date.isoformat(),
        "seats": sorted(numbers),
        "passengers": [
            {"seat": seat, "name": name, "document_type": document_type, "document": document}
            for seat, name, document_type, document in cleaned
        ],
        "total": total,
        "expires_at": expiration_time(status, created_at).isoformat(),
        "replaced_stripe_sessions": replaced_sessions,
    }


def _tickets_of_payment(cursor, user_id, payment_id):
    cursor.execute(
        """SELECT t.id, t.status
           FROM tickets t JOIN passengers p ON p.id = t.passenger_id
           WHERE t.payment_id = %s AND p.user_id = %s;""",
        (payment_id, user_id),
    )
    rows = cursor.fetchall()
    if not rows:
        raise PurchaseError("No encontramos esa compra", 404)
    return rows


def _apply_event_to_payment(cursor, user_id, payment_id, event):
    """Applies the event to every ticket of a purchase and returns the new status."""
    new_status = None
    for _, status in _tickets_of_payment(cursor, user_id, payment_id):
        new_status = next_status(status, event)
    cursor.execute("UPDATE tickets SET status = %s WHERE payment_id = %s;", (new_status, payment_id))
    return new_status


def get_payment_details(user_id, payment_id):
    """Checks that the purchase can be paid and returns what Stripe needs."""
    with connect() as connection, connection.cursor() as cursor:
        _expire_old_reservations(cursor)
        rows = _tickets_of_payment(cursor, user_id, payment_id)
        status = rows[0][1]
        if not purchase_state_machine(status).can(START_PAYMENT):
            raise PurchaseError(f"Esta compra no se puede pagar porque está {status}", 409)
        cursor.execute(
            """SELECT s.price, o.name, d.name, s.departure_time, MIN(t.travel_date), pm.stripe_session_id,
                      pm.expires_at
               FROM tickets t
               JOIN payments pm ON pm.id = t.payment_id
               JOIN schedules s ON s.id = t.schedule_id
               JOIN routes r ON r.id = s.route_id
               JOIN destinations o ON o.id = r.origin_id
               JOIN destinations d ON d.id = r.destination_id
               WHERE t.payment_id = %s
               GROUP BY s.price, o.name, d.name, s.departure_time, pm.stripe_session_id, pm.expires_at;""",
            (payment_id,),
        )
        price, origin, destination, departure_time, travel_date, stripe_session_id, expires_at = cursor.fetchone()
    return {
        "status": status,
        "unit_price": price,
        "quantity": len(rows),
        "description": f"Pasaje {origin} - {destination}, {travel_date.isoformat()} {departure_time.strftime('%H:%M')}",
        "stripe_session_id": stripe_session_id,
        "expires_at": expires_at.astimezone(COLOMBIA_TIMEZONE).isoformat() if expires_at else None,
    }


def mark_as_paying(user_id, payment_id, stripe_session_id, expires_at):
    """Saves the open Stripe session. The purchase is held exactly as long as that session lives."""
    with connect() as connection, connection.cursor() as cursor:
        status = _apply_event_to_payment(cursor, user_id, payment_id, START_PAYMENT)
        cursor.execute(
            "UPDATE payments SET stripe_session_id = %s, expires_at = %s WHERE id = %s;",
            (stripe_session_id, expires_at, payment_id),
        )
    return status


def confirm_payment(payment_id, user_id=None):
    """Marks a purchase as paid after Stripe confirmed the charge. user_id is None when the
    confirmation comes from the Stripe webhook. If the purchase had already expired, it tries
    to take the seats back; if someone else bought them, it raises SeatsLostError (refund)."""
    with connect() as connection, connection.cursor() as cursor:
        if user_id is None:
            cursor.execute("SELECT id, status FROM tickets WHERE payment_id = %s;", (payment_id,))
            rows = cursor.fetchall()
            if not rows:
                raise PurchaseError("No encontramos esa compra", 404)
        else:
            rows = _tickets_of_payment(cursor, user_id, payment_id)
        if all(status == PAID for _, status in rows):
            return PAID  # it was already confirmed (for example, the user reloaded the page)

        status = rows[0][1]
        event = CONFIRM_PAYMENT if status == PAYING else RECOVER_PAYMENT
        new_status = next_status(status, event)
        cursor.execute("SELECT stripe_session_id FROM payments WHERE id = %s;", (payment_id,))
        stripe_session_id = cursor.fetchone()[0]
        try:
            cursor.execute("UPDATE tickets SET status = %s WHERE payment_id = %s;", (new_status, payment_id))
        except psycopg.errors.UniqueViolation:
            raise SeatsLostError(payment_id, stripe_session_id)
        cursor.execute("UPDATE payments SET status = 'PAID' WHERE id = %s;", (payment_id,))
    return new_status


def mark_as_paid(user_id, payment_id):
    return confirm_payment(payment_id, user_id)


def mark_as_refunded(payment_id):
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("UPDATE payments SET status = 'REFUNDED' WHERE id = %s;", (payment_id,))


def cancel_purchase(user_id, payment_id):
    """Cancels an unpaid purchase. Returns (status, Stripe session to close or None)."""
    with connect() as connection, connection.cursor() as cursor:
        status = _apply_event_to_payment(cursor, user_id, payment_id, CANCEL)
        cursor.execute(
            "UPDATE payments SET status = 'CANCELLED' WHERE id = %s RETURNING stripe_session_id;", (payment_id,)
        )
        stripe_session_id = cursor.fetchone()[0]
    return status, stripe_session_id


MY_TICKETS_QUERY = """
    SELECT t.id, t.payment_id, t.status, t.travel_date, s.departure_time, c.name,
           o.name, d.name, st.number, p.name, p.document_type, p.document, s.price, pm.amount,
           pm.created_at, r.duration_min, pm.expires_at, pm.booking_code
    FROM tickets t
    JOIN passengers p ON p.id = t.passenger_id
    JOIN seats st ON st.id = t.seat_id
    JOIN payments pm ON pm.id = t.payment_id
    JOIN schedules s ON s.id = t.schedule_id
    JOIN routes r ON r.id = s.route_id
    JOIN companies c ON c.id = r.company_id
    JOIN destinations o ON o.id = r.origin_id
    JOIN destinations d ON d.id = r.destination_id
    WHERE p.user_id = %s
    ORDER BY pm.created_at DESC, t.payment_id DESC, st.number;
"""


def get_my_tickets(user_id, order=NEWEST_FIRST):
    """The user's purchase history: each purchase with its passengers and seats."""
    with connect() as connection, connection.cursor() as cursor:
        _expire_old_reservations(cursor)
        cursor.execute(MY_TICKETS_QUERY, (user_id,))
        rows = cursor.fetchall()

    purchases_by_payment = HashTable()
    purchases_in_order = []
    for row in rows:
        (ticket_id, payment_id, status, travel_date, departure_time, company, origin, destination,
         seat, passenger, document_type, document, price, amount, purchased_at, duration_min, payment_expires_at,
         booking_code) = row
        purchase = purchases_by_payment.get(payment_id)
        if purchase is None:
            expires_at = expiration_time(status, purchased_at, payment_expires_at)
            purchase = {
                "payment_id": payment_id,
                "booking_code": booking_code,
                "status": status,
                "date": travel_date.isoformat(),
                "departure_time": departure_time.strftime("%H:%M"),
                "duration_min": duration_min,
                "company": company,
                "origin": origin,
                "destination": destination,
                "unit_price": price,
                "total": amount,
                "purchased_at": purchased_at.astimezone(COLOMBIA_TIMEZONE).isoformat(),
                "expires_at": expires_at.strftime("%H:%M") if expires_at else None,
                "tickets": [],
            }
            purchases_by_payment.put(payment_id, purchase)
            purchases_in_order.append(purchase)
        purchase["tickets"].append(
            {"ticket_id": ticket_id, "seat": seat, "passenger": passenger,
             "document_type": document_type, "document": document}
        )
    return purchase_history(purchases_in_order, order)


def count_taken_seats_by_schedule(travel_date):
    """Hash table schedule_id -> seats already sold or held that day."""
    taken_by_schedule = HashTable()
    with connect() as connection, connection.cursor() as cursor:
        _expire_old_reservations(cursor)
        cursor.execute(
            """SELECT schedule_id, COUNT(*) FROM tickets
               WHERE travel_date = %s AND status IN ('RESERVED', 'PAYING', 'PAID')
               GROUP BY schedule_id;""",
            (travel_date,),
        )
        for schedule_id, count in cursor:
            taken_by_schedule.put(schedule_id, count)
    return taken_by_schedule
