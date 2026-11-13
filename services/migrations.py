"""Applies the additive database scripts on startup.

Scripts 06 onwards only add columns and indexes, so the backend runs the ones
the database does not have yet when it starts. That way a new version never
reaches Render before its columns exist in Neon. Each script runs once, in its
own transaction, and is recorded in the applied_migrations table.
"""

from pathlib import Path

from services.database import connect

SCRIPTS_FOLDER = Path(__file__).resolve().parent.parent / "db"
AUTOMATIC_SCRIPTS = (
    "06_payment_expiration.sql", "07_booking_codes.sql", "08_document_types.sql",
    "09_roles_and_settings.sql", "10_colombia_routes.sql", "11_app_settings.sql",
)


def split_statements(script):
    """Removes the "--" comment lines and splits the script into its SQL statements."""
    lines = [line for line in script.splitlines() if not line.strip().startswith("--")]
    return [statement.strip() for statement in "\n".join(lines).split(";") if statement.strip()]


def apply_pending_migrations(scripts=AUTOMATIC_SCRIPTS):
    """Runs the scripts that were never applied. Returns the names of those it ran."""
    applied_now = []
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS applied_migrations (
                   name TEXT PRIMARY KEY,
                   applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
               );"""
        )
        connection.commit()
        for name in scripts:
            cursor.execute("SELECT 1 FROM applied_migrations WHERE name = %s;", (name,))
            if cursor.fetchone():
                continue
            for statement in split_statements((SCRIPTS_FOLDER / name).read_text(encoding="utf-8")):
                cursor.execute(statement)
            cursor.execute("INSERT INTO applied_migrations (name) VALUES (%s);", (name,))
            connection.commit()  # each script is all or nothing
            applied_now.append(name)
    return applied_now
