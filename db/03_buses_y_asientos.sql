-- Script 3: buses, asientos y reglas para vender tiquetes.
-- Se ejecuta una sola vez en Neon (SQL Editor), después de tablas.sql,
-- datos.sql y 02_compra_y_chat.sql.

-- 1. Un bus por empresa, de 40 puestos (regla del sistema: 40 cupos por salida).
--    Las placas son de demostración.
INSERT INTO buses (empresa_id, placa, capacidad) VALUES
(1, 'TRP-101', 40),  -- TRANSIPIALES
(2, 'TSD-201', 40),  -- TRANSANDONA
(3, 'EXB-301', 40),  -- EXPRESO BOLIVARIANO
(4, 'CTB-401', 40);  -- CONTINENTAL BUS

-- 2. Los asientos 1 a 40 de cada bus.
INSERT INTO asientos (bus_id, numero)
SELECT b.id, n
FROM buses b
CROSS JOIN generate_series(1, 40) AS n;

-- 3. Un pago puede cubrir varios tiquetes (por ejemplo 3 asientos en una sola compra).
--    Por eso el tiquete apunta a su pago, y no al revés.
ALTER TABLE pagos DROP COLUMN tiquete_id;
ALTER TABLE tiquetes ADD COLUMN pago_id INTEGER REFERENCES pagos(id);

-- 4. Regla de oro: un mismo asiento no se puede vender dos veces en la misma
--    salida y fecha. Solo cuentan los tiquetes vivos (los cancelados o vencidos
--    liberan el asiento).
CREATE UNIQUE INDEX asiento_unico_por_viaje
ON tiquetes (horario_id, fecha_viaje, asiento_id)
WHERE estado IN ('RESERVADO', 'PAGANDO', 'PAGADO');
