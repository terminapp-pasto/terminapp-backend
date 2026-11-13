"""Queries on the users table."""

import psycopg

from services.database import connect


ROLE_USER = "user"
ROLE_COMPANY = "company"
ROLE_ADMIN = "admin"
ROLES = (ROLE_USER, ROLE_COMPANY, ROLE_ADMIN)

USER_COLUMNS = "u.id, u.name, u.email, u.role, u.company_id, c.name"
USER_TABLES = "users u LEFT JOIN companies c ON c.id = u.company_id"


def _user_from_row(row):
    return {"id": row[0], "name": row[1], "email": row[2], "role": row[3], "company_id": row[4], "company": row[5]}


def create_user(name, email, password_hash):
    """Saves a new user. Returns None if the email is already registered."""
    try:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id;",
                (name, email, password_hash),
            )
            user_id = cursor.fetchone()[0]
    except psycopg.errors.UniqueViolation:
        return None
    return {"id": user_id, "name": name, "email": email, "role": ROLE_USER, "company_id": None, "company": None}


def find_user_by_email(email):
    """Returns the user with its password_hash, or None if it does not exist."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(f"SELECT {USER_COLUMNS}, u.password_hash FROM {USER_TABLES} WHERE u.email = %s;", (email,))
        row = cursor.fetchone()
    if row is None:
        return None
    user = _user_from_row(row)
    user["password_hash"] = row[6]
    return user


def find_user_by_id(user_id):
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(f"SELECT {USER_COLUMNS} FROM {USER_TABLES} WHERE u.id = %s;", (user_id,))
        row = cursor.fetchone()
    return None if row is None else _user_from_row(row)


def upsert_user(name, email, password_hash, role=None):
    """Creates the user if missing, or sets this password if it already exists.
    With a role, it also gives the account that role (used for the admin account)."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, password_hash = EXCLUDED.password_hash, "
            "role = COALESCE(%s, users.role), "
            "company_id = CASE WHEN %s::text IS NULL THEN users.company_id ELSE NULL END;",
            (name, email, password_hash, role or ROLE_USER, role, role),
        )
