-- Script 4: buses, seats and the rule that prevents selling a seat twice.
-- Runs after 03_purchases_and_chat.sql.

-- 1. One 40-seat bus per company (system rule: 40 seats per departure).
--    The plates are for demonstration only.
INSERT INTO buses (company_id, plate, capacity) VALUES
(1, 'TRP-101', 40),  -- TRANSIPIALES
(2, 'TSD-201', 40),  -- TRANSANDONA
(3, 'EXB-301', 40),  -- EXPRESO BOLIVARIANO
(4, 'CTB-401', 40);  -- CONTINENTAL BUS

-- 2. Seats 1 to 40 of every bus.
INSERT INTO seats (bus_id, number)
SELECT b.id, n
FROM buses b
CROSS JOIN generate_series(1, 40) AS n;

-- 3. Golden rule: the same seat cannot be sold twice for the same departure
--    and date. Only live tickets count (cancelled or expired ones free the
--    seat). If two people ask for the last seat at the same instant, the
--    database accepts the first one and rejects the second.
CREATE UNIQUE INDEX unique_seat_per_trip
ON tickets (schedule_id, travel_date, seat_id)
WHERE status IN ('RESERVED', 'PAYING', 'PAID');
