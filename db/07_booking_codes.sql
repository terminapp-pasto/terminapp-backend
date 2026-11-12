-- Script 7: a booking code for every purchase, like the ones airlines give (for example "K7M2QX").
-- It is random, so nobody can guess another person's code. Safe to run on the live
-- database: existing purchases get a code too.

ALTER TABLE payments ADD COLUMN IF NOT EXISTS booking_code VARCHAR(6);

UPDATE payments
SET booking_code = upper(substr(md5(random()::text || id::text), 1, 6))
WHERE booking_code IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS unique_booking_code ON payments (booking_code);
