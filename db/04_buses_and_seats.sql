-- Script 4: buses, asientos y la regla que impide vender un asiento dos veces.
-- Se ejecuta después de 03_purchases_and_chat.sql.

-- 1. Un bus por empresa, de 40 puestos (regla del sistema: 40 cupos por salida).
--    Las placas son de demostración.
INSERT INTO buses (company_id, plate, capacity) VALUES
(1, 'TRP-101', 40),  -- TRANSIPIALES
(2, 'TSD-201', 40),  -- TRANSANDONA
(3, 'EXB-301', 40),  -- EXPRESO BOLIVARIANO
(4, 'CTB-401', 40);  -- CONTINENTAL BUS

-- 2. Los asientos 1 a 40 de cada bus.
INSERT INTO seats (bus_id, number)
SELECT b.id, n
FROM buses b
CROSS JOIN generate_series(1, 40) AS n;

-- 3. Regla de oro: un mismo asiento no se puede vender dos veces en la misma
--    salida y fecha. Solo cuentan los tiquetes vivos (los cancelados o vencidos
--    liberan el asiento). Si dos personas piden el último asiento en el mismo
--    instante, la base de datos acepta la primera y rechaza la segunda.
CREATE UNIQUE INDEX unique_seat_per_trip
ON tickets (schedule_id, travel_date, seat_id)
WHERE status IN ('RESERVED', 'PAYING', 'PAID');
