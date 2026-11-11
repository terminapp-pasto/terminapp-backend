"""Database connection. This is the only place that opens connections."""

import psycopg

import config


def connect():
    """Opens a connection. Used with "with", it commits on exit or rolls back on error."""
    return psycopg.connect(config.DATABASE_URL)
