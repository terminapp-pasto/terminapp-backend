-- Script 10: routes from Pasto to the main cities of Colombia.
-- Durations and prices are reference values for the class project (the usual road
-- times and fares of 2026), not an official timetable. The admin can change any price
-- from the admin panel.
-- Safe to run on the live database: it uses names instead of ids and only inserts
-- what does not exist yet, so running it twice changes nothing.

INSERT INTO destinations (name)
SELECT v.name
FROM (VALUES
    ('Popayán'), ('Túquerres'), ('La Unión'), ('Neiva'), ('Florencia'), ('Ibagué'),
    ('Armenia'), ('Pereira'), ('Manizales'), ('Medellín'), ('Villavicencio'), ('Tunja'),
    ('Bucaramanga'), ('Cartagena'), ('Barranquilla')
) AS v(name)
WHERE NOT EXISTS (SELECT 1 FROM destinations d WHERE d.name = v.name);

INSERT INTO routes (company_id, origin_id, destination_id, duration_min)
SELECT c.id, o.id, d.id, v.minutes
FROM (VALUES
    ('TRANSIPIALES', 'Túquerres', 120),
    ('TRANSANDONA', 'La Unión', 150),
    ('EXPRESO BOLIVARIANO', 'Popayán', 300),
    ('TRANSIPIALES', 'Popayán', 300),
    ('CONTINENTAL BUS', 'Neiva', 600),
    ('CONTINENTAL BUS', 'Florencia', 660),
    ('CONTINENTAL BUS', 'Ibagué', 900),
    ('EXPRESO BOLIVARIANO', 'Armenia', 720),
    ('EXPRESO BOLIVARIANO', 'Pereira', 780),
    ('EXPRESO BOLIVARIANO', 'Manizales', 840),
    ('EXPRESO BOLIVARIANO', 'Medellín', 1140),
    ('CONTINENTAL BUS', 'Villavicencio', 1320),
    ('CONTINENTAL BUS', 'Tunja', 1260),
    ('EXPRESO BOLIVARIANO', 'Bucaramanga', 1680),
    ('EXPRESO BOLIVARIANO', 'Cartagena', 1920),
    ('EXPRESO BOLIVARIANO', 'Barranquilla', 1980)
) AS v(company, destination, minutes)
JOIN companies c ON c.name = v.company
JOIN destinations o ON o.name = 'Pasto'
JOIN destinations d ON d.name = v.destination
WHERE NOT EXISTS (
    SELECT 1 FROM routes r WHERE r.company_id = c.id AND r.origin_id = o.id AND r.destination_id = d.id
);

INSERT INTO schedules (route_id, departure_time, price, seats, bus_id)
SELECT r.id, v.departure::time, v.price, b.capacity, b.id
FROM (VALUES
    ('TRANSIPIALES', 'Túquerres', '06:30', 15000), ('TRANSIPIALES', 'Túquerres', '09:30', 15000),
    ('TRANSIPIALES', 'Túquerres', '12:30', 15000), ('TRANSIPIALES', 'Túquerres', '16:30', 15000),
    ('TRANSANDONA', 'La Unión', '07:00', 20000), ('TRANSANDONA', 'La Unión', '14:00', 20000),
    ('EXPRESO BOLIVARIANO', 'Popayán', '07:00', 55000), ('EXPRESO BOLIVARIANO', 'Popayán', '13:00', 55000),
    ('EXPRESO BOLIVARIANO', 'Popayán', '23:00', 50000),
    ('TRANSIPIALES', 'Popayán', '09:00', 50000), ('TRANSIPIALES', 'Popayán', '15:00', 50000),
    ('CONTINENTAL BUS', 'Neiva', '07:30', 90000), ('CONTINENTAL BUS', 'Neiva', '19:00', 90000),
    ('CONTINENTAL BUS', 'Florencia', '06:30', 95000),
    ('CONTINENTAL BUS', 'Ibagué', '15:00', 120000),
    ('EXPRESO BOLIVARIANO', 'Armenia', '18:30', 115000),
    ('EXPRESO BOLIVARIANO', 'Pereira', '17:00', 120000), ('EXPRESO BOLIVARIANO', 'Pereira', '19:30', 120000),
    ('EXPRESO BOLIVARIANO', 'Manizales', '16:00', 125000),
    ('EXPRESO BOLIVARIANO', 'Medellín', '08:00', 150000), ('EXPRESO BOLIVARIANO', 'Medellín', '18:00', 150000),
    ('CONTINENTAL BUS', 'Villavicencio', '13:00', 170000),
    ('CONTINENTAL BUS', 'Tunja', '09:00', 175000),
    ('EXPRESO BOLIVARIANO', 'Bucaramanga', '12:00', 210000),
    ('EXPRESO BOLIVARIANO', 'Cartagena', '11:00', 245000),
    ('EXPRESO BOLIVARIANO', 'Barranquilla', '10:30', 250000)
) AS v(company, destination, departure, price)
JOIN companies c ON c.name = v.company
JOIN destinations o ON o.name = 'Pasto'
JOIN destinations d ON d.name = v.destination
JOIN routes r ON r.company_id = c.id AND r.origin_id = o.id AND r.destination_id = d.id
JOIN LATERAL (SELECT id, capacity FROM buses WHERE company_id = c.id ORDER BY id LIMIT 1) b ON TRUE
WHERE NOT EXISTS (
    SELECT 1 FROM schedules s WHERE s.route_id = r.id AND s.departure_time = v.departure::time
);
