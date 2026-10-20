"""Consultas a la tabla usuarios."""

import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def crear_usuario(nombre, correo, password_hash):
    """Guarda un usuario nuevo. Devuelve None si el correo ya está registrado."""
    try:
        with psycopg.connect(os.getenv("DATABASE_URL")) as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO usuarios (nombre, correo, password_hash) VALUES (%s, %s, %s) RETURNING id;",
                    (nombre, correo, password_hash),
                )
                usuario_id = cursor.fetchone()[0]
    except psycopg.errors.UniqueViolation:
        return None
    return {"id": usuario_id, "nombre": nombre, "correo": correo}


def buscar_por_correo(correo):
    """Devuelve el usuario con su password_hash, o None si no existe."""
    with psycopg.connect(os.getenv("DATABASE_URL")) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre, correo, password_hash FROM usuarios WHERE correo = %s;",
                (correo,),
            )
            fila = cursor.fetchone()
    if fila is None:
        return None
    return {"id": fila[0], "nombre": fila[1], "correo": fila[2], "password_hash": fila[3]}


def buscar_por_id(usuario_id):
    with psycopg.connect(os.getenv("DATABASE_URL")) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "SELECT id, nombre, correo FROM usuarios WHERE id = %s;", (usuario_id,)
            )
            fila = cursor.fetchone()
    if fila is None:
        return None
    return {"id": fila[0], "nombre": fila[1], "correo": fila[2]}
