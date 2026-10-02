CREATE TABLE empresas (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE destinos (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE rutas (
    id SERIAL PRIMARY KEY,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    origen_id INTEGER NOT NULL REFERENCES destinos(id),
    destino_id INTEGER NOT NULL REFERENCES destinos(id),
    duracion_min INTEGER NOT NULL
);

CREATE TABLE horarios (
    id SERIAL PRIMARY KEY,
    ruta_id INTEGER NOT NULL REFERENCES rutas(id),
    hora_salida TIME NOT NULL,
    precio INTEGER NOT NULL,
    cupos INTEGER NOT NULL
);

CREATE TABLE tiquetes (
    id SERIAL PRIMARY KEY,
    horario_id INTEGER NOT NULL REFERENCES horarios(id),
    fecha_viaje DATE NOT NULL,
    estado TEXT NOT NULL DEFAULT 'PENDIENTE',
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);