-- 08: document type of each passenger (CC, TI, CE or PA).
--
-- Additive and safe to run on a database that already has data: existing
-- passengers get 'CC' (national ID), which is what every purchase used so far.
-- Run it once, after 07_booking_codes.sql.

ALTER TABLE passengers ADD COLUMN IF NOT EXISTS document_type VARCHAR(2) NOT NULL DEFAULT 'CC';

ALTER TABLE passengers DROP CONSTRAINT IF EXISTS valid_document_type;
ALTER TABLE passengers ADD CONSTRAINT valid_document_type
    CHECK (document_type IN ('CC', 'TI', 'CE', 'PA'));
