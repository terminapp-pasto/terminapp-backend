"""Conexión con la base de datos. Es el único lugar que abre conexiones."""

import psycopg

import config


def connect():
    """Abre una conexión. Usada con "with", confirma al salir o deshace si hubo error."""
    return psycopg.connect(config.DATABASE_URL)
