-- Script 5: pasa a inglés la base de datos que ya existe en Neon, SIN perder datos.
-- Solo se ejecuta una vez, en una base creada con los scripts viejos en español.
-- Una base nueva no lo necesita: los scripts 01 a 04 ya crean todo en inglés.
-- Todo va dentro de una transacción: si algo falla, no cambia nada.

BEGIN;

-- 1. Tablas
ALTER TABLE empresas RENAME TO companies;
ALTER TABLE destinos RENAME TO destinations;
ALTER TABLE rutas RENAME TO routes;
ALTER TABLE horarios RENAME TO schedules;
ALTER TABLE tiquetes RENAME TO tickets;
ALTER TABLE usuarios RENAME TO users;
ALTER TABLE pasajeros RENAME TO passengers;
ALTER TABLE asientos RENAME TO seats;
ALTER TABLE pagos RENAME TO payments;
ALTER TABLE conversaciones RENAME TO conversations;
ALTER TABLE mensajes RENAME TO messages;

-- 2. Columnas
ALTER TABLE companies RENAME COLUMN nombre TO name;
ALTER TABLE destinations RENAME COLUMN nombre TO name;

ALTER TABLE routes RENAME COLUMN empresa_id TO company_id;
ALTER TABLE routes RENAME COLUMN origen_id TO origin_id;
ALTER TABLE routes RENAME COLUMN destino_id TO destination_id;
ALTER TABLE routes RENAME COLUMN duracion_min TO duration_min;

ALTER TABLE schedules RENAME COLUMN ruta_id TO route_id;
ALTER TABLE schedules RENAME COLUMN hora_salida TO departure_time;
ALTER TABLE schedules RENAME COLUMN precio TO price;
ALTER TABLE schedules RENAME COLUMN cupos TO seats;

ALTER TABLE tickets RENAME COLUMN horario_id TO schedule_id;
ALTER TABLE tickets RENAME COLUMN fecha_viaje TO travel_date;
ALTER TABLE tickets RENAME COLUMN estado TO status;
ALTER TABLE tickets RENAME COLUMN creado_en TO created_at;
ALTER TABLE tickets RENAME COLUMN pasajero_id TO passenger_id;
ALTER TABLE tickets RENAME COLUMN asiento_id TO seat_id;
ALTER TABLE tickets RENAME COLUMN pago_id TO payment_id;

ALTER TABLE users RENAME COLUMN nombre TO name;
ALTER TABLE users RENAME COLUMN correo TO email;
ALTER TABLE users RENAME COLUMN creado_en TO created_at;

ALTER TABLE passengers RENAME COLUMN usuario_id TO user_id;
ALTER TABLE passengers RENAME COLUMN nombre TO name;
ALTER TABLE passengers RENAME COLUMN documento TO document;

ALTER TABLE buses RENAME COLUMN empresa_id TO company_id;
ALTER TABLE buses RENAME COLUMN placa TO plate;
ALTER TABLE buses RENAME COLUMN capacidad TO capacity;

ALTER TABLE seats RENAME COLUMN numero TO number;

ALTER TABLE payments RENAME COLUMN valor TO amount;
ALTER TABLE payments RENAME COLUMN estado TO status;
ALTER TABLE payments RENAME COLUMN creado_en TO created_at;

ALTER TABLE conversations RENAME COLUMN usuario_id TO user_id;
ALTER TABLE conversations RENAME COLUMN creado_en TO created_at;

ALTER TABLE messages RENAME COLUMN conversacion_id TO conversation_id;
ALTER TABLE messages RENAME COLUMN rol TO role;
ALTER TABLE messages RENAME COLUMN contenido TO content;
ALTER TABLE messages RENAME COLUMN creado_en TO created_at;

-- 3. Estados en inglés. Primero se quita el índice que depende de ellos.
DROP INDEX asiento_unico_por_viaje;

UPDATE tickets SET status = CASE status
    WHEN 'RESERVADO' THEN 'RESERVED'
    WHEN 'PAGANDO' THEN 'PAYING'
    WHEN 'PAGADO' THEN 'PAID'
    WHEN 'CANCELADO' THEN 'CANCELLED'
    WHEN 'VENCIDO' THEN 'EXPIRED'
    WHEN 'PENDIENTE' THEN 'RESERVED'
    ELSE status
END;
ALTER TABLE tickets ALTER COLUMN status SET DEFAULT 'RESERVED';

UPDATE payments SET status = CASE status
    WHEN 'PENDIENTE' THEN 'PENDING'
    WHEN 'PAGADO' THEN 'PAID'
    WHEN 'CANCELADO' THEN 'CANCELLED'
    WHEN 'VENCIDO' THEN 'EXPIRED'
    ELSE status
END;
ALTER TABLE payments ALTER COLUMN status SET DEFAULT 'PENDING';

CREATE UNIQUE INDEX unique_seat_per_trip
ON tickets (schedule_id, travel_date, seat_id)
WHERE status IN ('RESERVED', 'PAYING', 'PAID');

-- 4. Roles del chat en inglés
ALTER TABLE messages DROP CONSTRAINT mensajes_rol_check;
UPDATE messages SET role = CASE role WHEN 'usuario' THEN 'user' ELSE 'assistant' END;
ALTER TABLE messages ADD CONSTRAINT messages_role_check CHECK (role IN ('user', 'assistant'));

-- 5. Límites de largo: los mismos que valida el backend, para que un texto
--    gigante no llegue nunca a la base de datos.
ALTER TABLE users ALTER COLUMN name TYPE VARCHAR(50) USING left(name, 50);
ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(100) USING left(email, 100);
ALTER TABLE passengers ALTER COLUMN name TYPE VARCHAR(50) USING left(name, 50);
ALTER TABLE passengers ALTER COLUMN document TYPE VARCHAR(12) USING left(document, 12);

COMMIT;
