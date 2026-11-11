"""Routes to check that the API and the database are alive."""

from fastapi import APIRouter

from services.database import connect

router = APIRouter(tags=["System"])


@router.get("/", summary="Welcome message")
def welcome():
    return {"message": "Hello World from the TerminAPP backend"}


@router.get("/health", summary="Checks the database connection")
def health():
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
    return {"database": "connected", "version": version}
