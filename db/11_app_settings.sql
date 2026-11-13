-- Script 11: general texts and rules of the app, editable from the admin panel
-- (home page, chat greeting, footer contact, notice banner, sales window, unpaid
-- purchases per user, boarding time and extra instructions for the AI).
-- A missing key means "use the default written in services/settings.py".
-- Safe to run on the live database: it only creates an empty table.

CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(40) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
