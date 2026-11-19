-- Script 12: baggage rules per company, set from the company's panel instead of the code.
--   max_checked_bags: bags in the hold each passenger may take (0 to 5; 2 by default)
--   bag_weight_kg:    maximum weight of each bag (5 to 50 kg; 20 by default)
-- Safe to run on the live database: existing companies keep the rule they had (2 bags of 20 kg).
-- The backend runs it by itself on startup (services/migrations.py).

ALTER TABLE companies ADD COLUMN IF NOT EXISTS max_checked_bags SMALLINT NOT NULL DEFAULT 2;
ALTER TABLE companies DROP CONSTRAINT IF EXISTS valid_max_checked_bags;
ALTER TABLE companies ADD CONSTRAINT valid_max_checked_bags CHECK (max_checked_bags BETWEEN 0 AND 5);

ALTER TABLE companies ADD COLUMN IF NOT EXISTS bag_weight_kg SMALLINT NOT NULL DEFAULT 20;
ALTER TABLE companies DROP CONSTRAINT IF EXISTS valid_bag_weight;
ALTER TABLE companies ADD CONSTRAINT valid_bag_weight CHECK (bag_weight_kg BETWEEN 5 AND 50);

-- A ticket may now carry up to the highest limit a company can choose
ALTER TABLE tickets DROP CONSTRAINT IF EXISTS valid_checked_bags;
ALTER TABLE tickets ADD CONSTRAINT valid_checked_bags CHECK (checked_bags BETWEEN 0 AND 5);
