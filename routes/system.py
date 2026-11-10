"""Rutas para comprobar que la API y la base de datos están vivas."""

from fastapi import APIRouter

from services.database import connect

router = APIRouter(tags=["Sistema"])


@router.get("/", summary="Mensaje de bienvenida")
def welcome():
    return {"message": "Hello World desde el backend de TerminAPP"}


@router.get("/health", summary="Comprueba la conexión con la base de datos")
def health():
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
    return {"database": "connected", "version": version}
