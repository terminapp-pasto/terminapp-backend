"""Routes to check that the API and the database are alive."""

from fastapi import APIRouter

from services.database import connect

router = APIRouter(tags=["System"])


@router.get("/", summary="Welcome message")
def welcome():
    return {"message": "Hello World from the TerminAPP backend"}


@router.get("/health", summary="Checks the database connection")
def health():
    # it does not reveal the database or system version: that only helps an attacker
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT 1;")
    return {"database": "connected"}
