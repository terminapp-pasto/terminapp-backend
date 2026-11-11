-- Script 3: tables for accounts, purchases, payments and the AI chat.
-- Runs after 01_tables.sql and 02_seed_data.sql.
-- The length limits (VARCHAR) are the same ones the backend validates.

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One passenger per ticket: buying 3 seats stores 3 passengers.
CREATE TABLE passengers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name VARCHAR(50) NOT NULL,
    document VARCHAR(12) NOT NULL
);

CREATE TABLE buses (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    plate TEXT NOT NULL UNIQUE,
    capacity INTEGER NOT NULL
);

CREATE TABLE seats (
    id SERIAL PRIMARY KEY,
    bus_id INTEGER NOT NULL REFERENCES buses(id),
    number INTEGER NOT NULL,
    UNIQUE (bus_id, number)
);

-- One payment covers every ticket of a purchase (for example 3 seats).
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    stripe_session_id TEXT UNIQUE,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE tickets
    ADD COLUMN passenger_id INTEGER REFERENCES passengers(id),
    ADD COLUMN seat_id INTEGER REFERENCES seats(id),
    ADD COLUMN payment_id INTEGER REFERENCES payments(id);
