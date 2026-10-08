-- Migración 2: tablas para la autenticación, la compra, el pago y el chat con la IA.
-- Se ejecuta después de tablas.sql y datos.sql.

CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pasajeros (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    nombre TEXT NOT NULL,
    documento TEXT NOT NULL
);

CREATE TABLE buses (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    placa TEXT NOT NULL UNIQUE,
    capacidad INTEGER NOT NULL
);

CREATE TABLE asientos (
    id SERIAL PRIMARY KEY,
    bus_id INTEGER NOT NULL REFERENCES buses(id),
    numero INTEGER NOT NULL,
    UNIQUE (bus_id, numero)
);

CREATE TABLE pagos (
    id SERIAL PRIMARY KEY,
    tiquete_id INTEGER NOT NULL REFERENCES tiquetes(id),
    stripe_session_id TEXT UNIQUE,
    valor INTEGER NOT NULL,
    estado TEXT NOT NULL DEFAULT 'PENDIENTE',
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE conversaciones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE mensajes (
    id SERIAL PRIMARY KEY,
    conversacion_id INTEGER NOT NULL REFERENCES conversaciones(id),
    rol TEXT NOT NULL CHECK (rol IN ('usuario', 'asistente')),
    contenido TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE tiquetes
    ADD COLUMN pasajero_id INTEGER REFERENCES pasajeros(id),
    ADD COLUMN asiento_id INTEGER REFERENCES asientos(id);