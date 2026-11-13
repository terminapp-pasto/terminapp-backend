"""Settings that live in the database: document types and company rules.

The admin changes them from the admin panel, so nothing here is hardcoded.
"""

from services.database import connect
from services.validation import build_document_type

DOCUMENT_TYPES_QUERY = """
    SELECT code, name, min_length, max_length, allows_letters, active
    FROM document_types ORDER BY code;
"""


def read_document_types(cursor, only_active=True):
    """Rows of the document_types table as dictionaries."""
    cursor.execute(DOCUMENT_TYPES_QUERY)
    rows = [
        {"code": code, "name": name, "min_length": min_length, "max_length": max_length,
         "allows_letters": allows_letters, "active": active}
        for code, name, min_length, max_length, allows_letters, active in cursor.fetchall()
    ]
    return [row for row in rows if row["active"]] if only_active else rows


def document_type_rules(cursor):
    """code -> (name, pattern, rule) of the active types, the format services/validation.py uses."""
    return {
        row["code"]: build_document_type(row["name"], row["min_length"], row["max_length"], row["allows_letters"])
        for row in read_document_types(cursor)
    }


def list_document_types():
    """The active document types, for the purchase form."""
    with connect() as connection, connection.cursor() as cursor:
        types = read_document_types(cursor)
    for row in types:
        row["rule"] = build_document_type(row["name"], row["min_length"], row["max_length"], row["allows_letters"])[2]
        del row["active"]
    return types
