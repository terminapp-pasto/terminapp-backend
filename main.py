"""Entry point of the TerminAPP API.

It only assembles the application: routes live in routes/, business logic in
services/ and the data structures in structs/.
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
from services.migrations import apply_pending_migrations
from services.users import upsert_user

API_VERSION = "2.0.0"
INVALID_DATA_MESSAGE = "Algunos datos no son válidos o son demasiado largos. Revísalos e intenta de nuevo."


def create_test_account():
    """Creates the professor's test account, only if its data is in the environment."""
    if not (config.TEST_ACCOUNT_EMAIL and config.TEST_ACCOUNT_PASSWORD):
        return
    try:
        upsert_user(
            config.TEST_ACCOUNT_NAME,
            config.TEST_ACCOUNT_EMAIL.strip().lower(),
            encrypt_password(config.TEST_ACCOUNT_PASSWORD),
        )
    except psycopg.Error as error:
        # If the database does not answer, the API starts anyway
        print(f"Could not create the test account: {error}")


def update_database():
    """Adds the columns that this version needs, if the database does not have them yet."""
    try:
        applied = apply_pending_migrations()
        if applied:
            print(f"Database scripts applied: {', '.join(applied)}")
    except (psycopg.Error, OSError) as error:
        # If the database does not answer, the API starts anyway
        print(f"Could not update the database: {error}")


@asynccontextmanager
async def on_startup(_app):
    update_database()
    create_test_account()
    yield


app = FastAPI(
    lifespan=on_startup,
    title="TerminAPP Backend",
    version=API_VERSION,
    description=(
        "TerminAPP API: bus ticket search from the Pasto bus terminal, AI chat, "
        "user accounts and purchases with Stripe test payments. "
        "Routes marked 🔒 need the login token: use the **Authorize** button."
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
    """Malformed or too long data: a clear message instead of a technical error."""
    return JSONResponse(status_code=400, content={"detail": INVALID_DATA_MESSAGE})


app.include_router(system.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(purchases.router)
