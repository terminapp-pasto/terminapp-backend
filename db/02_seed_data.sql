-- Real data checked on October 1, 2026.
-- Companies and destinations: official directory terminalpasto.gov.co
-- Departures, prices and durations: pinbus.com (Sandoná: redbus.co)
-- Seats: TerminAPP system rule (40 seats on sale per departure)

-- DESTINATIONS (id 1 to 7)
INSERT INTO destinations (name) VALUES
('Pasto'),     -- 1
('Ipiales'),   -- 2
('Sandoná'),   -- 3
('Tumaco'),    -- 4
('Mocoa'),     -- 5
('Cali'),      -- 6
('Bogotá');    -- 7

-- COMPANIES (id 1 to 4)
INSERT INTO companies (name) VALUES
('TRANSIPIALES'),          -- 1
('TRANSANDONA'),           -- 2
('EXPRESO BOLIVARIANO'),   -- 3
('CONTINENTAL BUS');       -- 4

-- ROUTES (id 1 to 8): company, origin, destination, travel minutes
INSERT INTO routes (company_id, origin_id, destination_id, duration_min) VALUES
(4, 1, 2,  100),  -- 1 Continental   Pasto → Ipiales  (1h 40m)
(3, 1, 2,  100),  -- 2 Bolivariano   Pasto → Ipiales  (1h 40m)
(2, 1, 3,  135),  -- 3 Transandoná   Pasto → Sandoná  (2h 15m)
(1, 1, 4,  360),  -- 4 Transipiales  Pasto → Tumaco   (6h 00m)
(1, 1, 5,  320),  -- 5 Transipiales  Pasto → Mocoa    (5h 20m)
(3, 1, 6,  580),  -- 6 Bolivariano   Pasto → Cali     (9h 40m)
(1, 1, 6,  580),  -- 7 Transipiales  Pasto → Cali     (9h 40m)
(4, 1, 7, 1100);  -- 8 Continental   Pasto → Bogotá   (18h 20m)

-- SCHEDULES (27 departures): route, time, price, seats
INSERT INTO schedules (route_id, departure_time, price, seats) VALUES
-- Pasto → Ipiales
(1, '10:18',  16000, 40), (1, '15:18',  16000, 40), (1, '18:18',  16000, 40),
(2, '03:49',  21000, 40), (2, '08:19',  21000, 40),
-- Pasto → Sandoná
(3, '06:00',   8000, 40), (3, '16:00',   8000, 40),
-- Pasto → Tumaco
(4, '00:30',  65000, 40), (4, '08:30',  65000, 40), (4, '10:30',  65000, 40),
(4, '13:15',  65000, 40), (4, '15:45',  65000, 40),
-- Pasto → Mocoa
(5, '05:15',  70000, 40), (5, '06:15',  70000, 40), (5, '08:00',  70000, 40),
(5, '11:45',  70000, 40), (5, '13:15',  70000, 40),
-- Pasto → Cali
(6, '12:30',  80000, 40), (6, '20:30',  72000, 40),
(6, '21:00',  61000, 40), (6, '22:00',  72000, 40),
(7, '20:00',  90000, 40),
-- Pasto → Bogotá
(8, '10:00', 160000, 40), (8, '14:30', 160000, 40), (8, '16:30', 160000, 40),
(8, '18:00', 160000, 40), (8, '22:00', 160000, 40);