-- Script 1: tablas del catálogo de viajes (empresas, municipios, rutas y salidas).

CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE destinations (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE routes (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    origin_id INTEGER NOT NULL REFERENCES destinations(id),
    destination_id INTEGER NOT NULL REFERENCES destinations(id),
    duration_min INTEGER NOT NULL
);

CREATE TABLE schedules (
    id SERIAL PRIMARY KEY,
    route_id INTEGER NOT NULL REFERENCES routes(id),
    departure_time TIME NOT NULL,
    price INTEGER NOT NULL,
    seats INTEGER NOT NULL
);

CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    schedule_id INTEGER NOT NULL REFERENCES schedules(id),
    travel_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'RESERVED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
