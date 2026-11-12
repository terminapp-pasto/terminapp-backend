-- Script 6: stores when each open Stripe payment expires.
-- The purchase is now held exactly as long as its Stripe session lives, so nobody
-- can pay for seats that were already released. Safe to run on the live database:
-- it only adds an empty column.

ALTER TABLE payments ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
