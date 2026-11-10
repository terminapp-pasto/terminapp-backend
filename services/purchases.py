"""Compra de pasajes: asientos, reservas, vencimientos e historial.

Aquí trabajan juntas las 5 estructuras de la compra:
- HashTable: mapa de asientos de una salida (número -> estado), consulta O(1).
- Stack: registro para deshacer cuando se reservan varios asientos y uno falla.
- Queue: reservas pendientes por orden de llegada, para vencer las viejas.
- StateMachine: decide qué cambios de estado son válidos para un tiquete.
- DoublyLinkedList: historial de compras del usuario, recorrible en los dos sentidos.

Concurrencia (dos personas pidiendo el último asiento al mismo tiempo):
1. Al reservar se bloquea la fila de la salida (SELECT ... FOR UPDATE). PostgreSQL
   pone en fila (cola FIFO) a las demás reservas de esa salida: la segunda espera
   a que la primera termine y luego ve el asiento ya ocupado.
2. Como red de seguridad, el índice único unique_seat_per_trip impide que dos
   tiquetes vivos tengan el mismo asiento en la misma salida y fecha.
"""

from datetime import datetime, timedelta, timezone

import psycopg

from services.database import connect
from services.dates import COLOMBIA_TIMEZONE, SALES_WINDOW_DAYS, now_in_colombia
from services.validation import (
    DOCUMENT_RULE, NAME_RULE, is_valid_document, is_valid_name, normalize_spaces,
)
from structs.doubly_linked_list import DoublyLinkedList
from structs.hash_table import HashTable
from structs.queue import Queue
from structs.stack import Stack
from structs.state_machine import (
    CANCEL, CONFIRM_PAYMENT, EXPIRE, PAID, PAYING, RESERVE, RESERVED, SELECTING, START_PAYMENT,
    TransitionError, purchase_state_machine,
)

RESERVATION_MINUTES = 15   # tiempo para empezar a pagar
PAYMENT_MINUTES = 45       # tiempo total para terminar de pagar (15 + 30 de Stripe)
MAX_SEATS_PER_PURCHASE = 5

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


class PurchaseError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ------------------------------------------------------------------
# Lógica pura con las estructuras (no toca la base de datos)
# ------------------------------------------------------------------

def build_seat_map(capacity, taken_numbers):
    """Crea la tabla hash con todos los asientos FREE y marca los ocupados."""
    seat_map = HashTable(capacity * 2)
    for number in range(1, capacity + 1):
        seat_map.put(number, FREE)
    for number in taken_numbers:
        seat_map.put(number, TAKEN)
    return seat_map


def seats_in_order(seat_map, capacity):
    """Pasa el mapa a la lista ordenada que se envía al frontend."""
    return [{"number": n, "status": seat_map.get(n)} for n in range(1, capacity + 1)]


def hold_seats(seat_map, numbers):
    """Aparta cada asiento pedido. Si alguno ya está ocupado, deshace los anteriores
    con la pila (en orden inverso) y devuelve ese número; si todo sale bien, None."""
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
    """Recibe (id, estado, creado) ordenados del más viejo al más nuevo y devuelve
    los ids que ya vencieron. Usa una cola por cada tipo de espera: como están en
    orden de llegada, basta mirar el frente y parar en el primero que sigue a tiempo."""
    reserved_queue, paying_queue = Queue(), Queue()
    for ticket in pending_tickets:
        (reserved_queue if ticket[1] == RESERVED else paying_queue).enqueue(ticket)

    expired_ids = []
    for queue, minutes in ((reserved_queue, RESERVATION_MINUTES), (paying_queue, PAYMENT_MINUTES)):
        deadline = now - timedelta(minutes=minutes)
        while not queue.is_empty() and queue.peek()[2] < deadline:
            ticket_id, status, _ = queue.dequeue()
            purchase_state_machine(status).trigger(EXPIRE)
            expired_ids.append(ticket_id)
    return expired_ids


def purchase_history(purchases, order=NEWEST_FIRST):
    """Arma la lista doble (más reciente en la cabeza) y la recorre en el sentido pedido."""
    history = DoublyLinkedList()
    for purchase in purchases:  # llegan de la más reciente a la más antigua
        history.append(purchase)
    result = []
    if order == OLDEST_FIRST:
        history.traverse_backward(result.append)
    else:
        history.traverse_forward(result.append)
    return result


def next_status(current_status, event):
    """Pregunta a la máquina de estados a qué estado se pasa; si no se puede, PurchaseError."""
    try:
        return purchase_state_machine(current_status).trigger(event)
    except TransitionError as error:
        raise PurchaseError(str(error), 409)


def expiration_time(status, created_at):
    """Hora de Colombia hasta la que se guarda una reserva sin pagar (None si no aplica)."""
    minutes = {RESERVED: RESERVATION_MINUTES, PAYING: PAYMENT_MINUTES}.get(status)
    if minutes is None:
        return None
    return (created_at + timedelta(minutes=minutes)).astimezone(COLOMBIA_TIMEZONE)


def clean_passengers(passengers):
    """Valida los pasajeros (uno por asiento) y devuelve [(asiento, nombre, documento)]."""
    if not passengers:
        raise PurchaseError("Elige al menos un asiento")
    if len(passengers) > MAX_SEATS_PER_PURCHASE:
        raise PurchaseError(f"Puedes comprar máximo {MAX_SEATS_PER_PURCHASE} asientos por compra")

    cleaned = []
    seen_seats = HashTable()
    for position, passenger in enumerate(passengers, start=1):
        seat = passenger["seat"]
        name = normalize_spaces(passenger["name"])
        document = str(passenger["document"]).strip()
        if seen_seats.contains(seat):
            raise PurchaseError(f"El asiento {seat} está repetido")
        seen_seats.put(seat, True)
        if not is_valid_name(name):
            raise PurchaseError(f"Pasajero {position}: {NAME_RULE}")
        if not is_valid_document(document):
            raise PurchaseError(f"Pasajero {position}: {DOCUMENT_RULE}")
        cleaned.append((seat, name, document))
    return cleaned


# ------------------------------------------------------------------
# Consultas
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


def _expire_old_reservations(cursor):
    cursor.execute(
        "SELECT id, status, created_at FROM tickets WHERE status IN ('RESERVED', 'PAYING') ORDER BY created_at;"
    )
    expired_ids = find_expired(cursor.fetchall(), datetime.now(timezone.utc))
    if expired_ids:
        cursor.execute("UPDATE tickets SET status = 'EXPIRED' WHERE id = ANY(%s);", (expired_ids,))
        cursor.execute(
            """UPDATE payments SET status = 'EXPIRED'
               WHERE status = 'PENDING' AND id IN (SELECT payment_id FROM tickets WHERE id = ANY(%s));""",
            (expired_ids,),
        )


def _get_departure(cursor, schedule_id, lock=False):
    cursor.execute(DEPARTURE_QUERY, (schedule_id,))
    row = cursor.fetchone()
    if row is None:
        raise PurchaseError("Esa salida no existe", 404)
    if lock:
        # Pone en fila a las demás reservas de esta salida hasta que esta termine
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
    """Si el usuario ya tenía una compra sin pagar para este mismo viaje, la cancela
    para que nunca queden dos pagos en proceso. Devuelve las sesiones de Stripe a cerrar."""
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
    """Aparta los asientos (un pasajero por asiento) por RESERVATION_MINUTES minutos.
    passengers: lista de {"seat", "name", "document"}."""
    cleaned = clean_passengers(passengers)
    numbers = [seat for seat, _, _ in cleaned]

    with connect() as connection, connection.cursor() as cursor:
        _expire_old_reservations(cursor)
        departure = _get_departure(cursor, schedule_id, lock=True)
        _check_travel_date(travel_date, departure)

        for number in numbers:
            if number < 1 or number > departure["capacity"]:
                raise PurchaseError(f"El asiento {number} no existe en este bus")

        replaced_sessions = _cancel_pending_purchases_for_trip(cursor, user_id, schedule_id, travel_date)

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
        cursor.execute(
            "INSERT INTO payments (amount, status) VALUES (%s, 'PENDING') RETURNING id, created_at;", (total,)
        )
        payment_id, created_at = cursor.fetchone()

        status = next_status(SELECTING, RESERVE)
        try:
            for number, name, document in cleaned:
                cursor.execute(
                    "INSERT INTO passengers (user_id, name, document) VALUES (%s, %s, %s) RETURNING id;",
                    (user_id, name, document),
                )
                passenger_id = cursor.fetchone()[0]
                cursor.execute(
                    """INSERT INTO tickets (schedule_id, travel_date, status, passenger_id, seat_id, payment_id)
                       VALUES (%s, %s, %s, %s, %s, %s);""",
                    (schedule_id, travel_date, status, passenger_id, seat_ids.get(number), payment_id),
                )
        except psycopg.errors.UniqueViolation:
            # otra persona apartó el asiento en el mismo instante: el índice único lo impidió
            raise PurchaseError("Uno de los asientos acaba de ser ocupado. Elige otro", 409)

    return {
        "payment_id": payment_id,
        "status": status,
        "departure": departure,
        "date": travel_date.isoformat(),
        "seats": sorted(numbers),
        "passengers": [{"seat": seat, "name": name, "document": document} for seat, name, document in cleaned],
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
    """Aplica el evento a todos los tiquetes de una compra y devuelve el estado nuevo."""
    new_status = None
    for _, status in _tickets_of_payment(cursor, user_id, payment_id):
        new_status = next_status(status, event)
    cursor.execute("UPDATE tickets SET status = %s WHERE payment_id = %s;", (new_status, payment_id))
    return new_status


def get_payment_details(user_id, payment_id):
    """Revisa que la compra se pueda pagar y devuelve lo que Stripe necesita."""
    with connect() as connection, connection.cursor() as cursor:
        _expire_old_reservations(cursor)
        rows = _tickets_of_payment(cursor, user_id, payment_id)
        status = rows[0][1]
        if not purchase_state_machine(status).can(START_PAYMENT):
            raise PurchaseError(f"Esta compra no se puede pagar porque está {status}", 409)
        cursor.execute(
            """SELECT s.price, o.name, d.name, s.departure_time, MIN(t.travel_date), pm.stripe_session_id
               FROM tickets t
               JOIN payments pm ON pm.id = t.payment_id
               JOIN schedules s ON s.id = t.schedule_id
               JOIN routes r ON r.id = s.route_id
               JOIN destinations o ON o.id = r.origin_id
               JOIN destinations d ON d.id = r.destination_id
               WHERE t.payment_id = %s
               GROUP BY s.price, o.name, d.name, s.departure_time, pm.stripe_session_id;""",
            (payment_id,),
        )
        price, origin, destination, departure_time, travel_date, stripe_session_id = cursor.fetchone()
    return {
        "status": status,
        "unit_price": price,
        "quantity": len(rows),
        "description": f"Pasaje {origin} - {destination}, {travel_date.isoformat()} {departure_time.strftime('%H:%M')}",
        "stripe_session_id": stripe_session_id,
    }


def mark_as_paying(user_id, payment_id, stripe_session_id):
    with connect() as connection, connection.cursor() as cursor:
        status = _apply_event_to_payment(cursor, user_id, payment_id, START_PAYMENT)
        cursor.execute("UPDATE payments SET stripe_session_id = %s WHERE id = %s;", (stripe_session_id, payment_id))
    return status


def mark_as_paid(user_id, payment_id):
    with connect() as connection, connection.cursor() as cursor:
        rows = _tickets_of_payment(cursor, user_id, payment_id)
        if all(status == PAID for _, status in rows):
            return PAID  # ya estaba confirmado (por ejemplo, el usuario recargó la página)
        status = _apply_event_to_payment(cursor, user_id, payment_id, CONFIRM_PAYMENT)
        cursor.execute("UPDATE payments SET status = 'PAID' WHERE id = %s;", (payment_id,))
    return status


def cancel_purchase(user_id, payment_id):
    """Cancela una compra sin pagar. Devuelve (estado, sesión de Stripe a cerrar o None)."""
    with connect() as connection, connection.cursor() as cursor:
        status = _apply_event_to_payment(cursor, user_id, payment_id, CANCEL)
        cursor.execute(
            "UPDATE payments SET status = 'CANCELLED' WHERE id = %s RETURNING stripe_session_id;", (payment_id,)
        )
        stripe_session_id = cursor.fetchone()[0]
    return status, stripe_session_id


MY_TICKETS_QUERY = """
    SELECT t.id, t.payment_id, t.status, t.travel_date, s.departure_time, c.name,
           o.name, d.name, st.number, p.name, p.document, s.price, pm.amount,
           pm.created_at, r.duration_min
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
    """Historial de compras del usuario: cada compra con sus pasajeros y asientos."""
    with connect() as connection, connection.cursor() as cursor:
        _expire_old_reservations(cursor)
        cursor.execute(MY_TICKETS_QUERY, (user_id,))
        rows = cursor.fetchall()

    purchases_by_payment = HashTable()
    purchases_in_order = []
    for row in rows:
        (ticket_id, payment_id, status, travel_date, departure_time, company, origin, destination,
         seat, passenger, document, price, amount, purchased_at, duration_min) = row
        purchase = purchases_by_payment.get(payment_id)
        if purchase is None:
            expires_at = expiration_time(status, purchased_at)
            purchase = {
                "payment_id": payment_id,
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
            {"ticket_id": ticket_id, "seat": seat, "passenger": passenger, "document": document}
        )
    return purchase_history(purchases_in_order, order)


def count_taken_seats_by_schedule(travel_date):
    """Tabla hash schedule_id -> asientos ya vendidos o apartados ese día."""
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
