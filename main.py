"""Punto de entrada de la API de TerminAPP.

Solo arma la aplicación: las rutas viven en la carpeta routes/, la lógica en
services/ y las estructuras de datos en structs/.
"""

from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from authentication.utilities import encrypt_password
from routes import auth, chat, purchases, search, system
from services.users import upsert_user

API_VERSION = "2.0.0"
INVALID_DATA_MESSAGE = "Algunos datos no son válidos o son demasiado largos. Revísalos e intenta de nuevo."


def create_test_account():
    """Crea la cuenta de prueba del profesor, solo si sus datos están en el entorno."""
    if not (config.TEST_ACCOUNT_EMAIL and config.TEST_ACCOUNT_PASSWORD):
        return
    try:
        upsert_user(
            config.TEST_ACCOUNT_NAME,
            config.TEST_ACCOUNT_EMAIL.strip().lower(),
            encrypt_password(config.TEST_ACCOUNT_PASSWORD),
        )
    except psycopg.Error as error:
        # Si la base de datos no responde, la API arranca igual
        print(f"No se pudo crear la cuenta de prueba: {error}")


@asynccontextmanager
async def on_startup(_app):
    create_test_account()
    yield


app = FastAPI(
    lifespan=on_startup,
    title="TerminAPP Backend",
    version=API_VERSION,
    description=(
        "API de TerminAPP: búsqueda de pasajes desde la Terminal de Transportes de Pasto, "
        "chat con IA, cuentas de usuario y compra con pago de prueba en Stripe. "
        "Las rutas con 🔒 necesitan el token del inicio de sesión: usa el botón **Authorize**."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=config.ALLOWED_ORIGINS_PATTERN,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def handle_invalid_request(_request: Request, error: RequestValidationError):
    """Datos mal formados o demasiado largos: un mensaje claro en vez de un error técnico."""
    return JSONResponse(status_code=400, content={"detail": INVALID_DATA_MESSAGE})


app.include_router(system.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(purchases.router)
