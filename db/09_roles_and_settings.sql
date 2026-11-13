-- Script 9: roles, per-company settings, a bus for every departure, the contact phone,
-- checked luggage and the document types stored in the database.
-- Safe to run on the live database: it only adds columns, a table and constraints,
-- and fills the new columns with the values the app used until now.

-- 1. Roles: a normal traveller (user), a bus company employee (company) or the terminal admin (admin).
--    A company user only manages its own company (company_id).
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(10) NOT NULL DEFAULT 'user';
ALTER TABLE users DROP CONSTRAINT IF EXISTS valid_role;
ALTER TABLE users ADD CONSTRAINT valid_role CHECK (role IN ('user', 'company', 'admin'));
ALTER TABLE users ADD COLUMN IF NOT EXISTS company_id INTEGER REFERENCES companies(id);

-- 2. Settings of each company: seats per purchase and how long an unpaid purchase holds the seats.
ALTER TABLE companies ADD COLUMN IF NOT EXISTS max_seats_per_purchase SMALLINT NOT NULL DEFAULT 5;
ALTER TABLE companies DROP CONSTRAINT IF EXISTS valid_max_seats;
ALTER TABLE companies ADD CONSTRAINT valid_max_seats CHECK (max_seats_per_purchase BETWEEN 1 AND 10);
ALTER TABLE companies ADD COLUMN IF NOT EXISTS reservation_minutes SMALLINT NOT NULL DEFAULT 10;
ALTER TABLE companies DROP CONSTRAINT IF EXISTS valid_reservation_minutes;
ALTER TABLE companies ADD CONSTRAINT valid_reservation_minutes CHECK (reservation_minutes BETWEEN 5 AND 30);

-- 3. The bus that makes each departure (its capacity is the number of seats on sale).
--    Existing departures get the first bus of their company, which is what the app used so far.
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS bus_id INTEGER REFERENCES buses(id);
UPDATE schedules s
SET bus_id = (
    SELECT b.id FROM buses b JOIN routes r ON r.company_id = b.company_id
    WHERE r.id = s.route_id ORDER BY b.id LIMIT 1
)
WHERE s.bus_id IS NULL;

-- A departure can be taken off sale without deleting it (its tickets stay in the history).
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

-- 4. Contact phone of the purchase and checked bags of each passenger.
ALTER TABLE payments ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(10);
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS checked_bags SMALLINT NOT NULL DEFAULT 0;
ALTER TABLE tickets DROP CONSTRAINT IF EXISTS valid_checked_bags;
ALTER TABLE tickets ADD CONSTRAINT valid_checked_bags CHECK (checked_bags BETWEEN 0 AND 2);

-- 5. Document types accepted for travel. The admin can add more or turn one off.
CREATE TABLE IF NOT EXISTS document_types (
    code VARCHAR(2) PRIMARY KEY,
    name VARCHAR(40) NOT NULL,
    min_length SMALLINT NOT NULL CHECK (min_length BETWEEN 3 AND 12),
    max_length SMALLINT NOT NULL CHECK (max_length BETWEEN 3 AND 12),
    allows_letters BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (min_length <= max_length)
);

INSERT INTO document_types (code, name, min_length, max_length, allows_letters) VALUES
('CC', 'Cédula de ciudadanía', 5, 10, FALSE),
('TI', 'Tarjeta de identidad', 10, 11, FALSE),
('CE', 'Cédula de extranjería', 5, 12, FALSE),
('PA', 'Pasaporte', 5, 12, TRUE)
ON CONFLICT (code) DO NOTHING;

-- The fixed list (CC, TI, CE, PA) is replaced by a reference to the table.
ALTER TABLE passengers DROP CONSTRAINT IF EXISTS valid_document_type;
ALTER TABLE passengers DROP CONSTRAINT IF EXISTS passengers_document_type_fk;
ALTER TABLE passengers ADD CONSTRAINT passengers_document_type_fk
    FOREIGN KEY (document_type) REFERENCES document_types(code);
