"""Consultas a la tabla users."""

import psycopg

from services.database import connect


def _user_from_row(row):
    return {"id": row[0], "name": row[1], "email": row[2]}


def create_user(name, email, password_hash):
    """Guarda un usuario nuevo. Devuelve None si el correo ya está registrado."""
    try:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id;",
                (name, email, password_hash),
            )
            user_id = cursor.fetchone()[0]
    except psycopg.errors.UniqueViolation:
        return None
    return {"id": user_id, "name": name, "email": email}


def find_user_by_email(email):
    """Devuelve el usuario con su password_hash, o None si no existe."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id, name, email, password_hash FROM users WHERE email = %s;", (email,))
        row = cursor.fetchone()
    if row is None:
        return None
    user = _user_from_row(row)
    user["password_hash"] = row[3]
    return user


def find_user_by_id(user_id):
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id, name, email FROM users WHERE id = %s;", (user_id,))
        row = cursor.fetchone()
    return None if row is None else _user_from_row(row)


def upsert_user(name, email, password_hash):
    """Crea el usuario si no existe, o le pone esta contraseña si ya existe."""
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) "
            "ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name, password_hash = EXCLUDED.password_hash;",
            (name, email, password_hash),
        )
