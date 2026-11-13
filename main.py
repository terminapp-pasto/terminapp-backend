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
from routes import admin, auth, chat, purchases, search, system
from services.migrations import apply_pending_migrations
from services.users import ROLE_ADMIN, upsert_user

API_VERSION = "2.0.0"
INVALID_DATA_MESSAGE = "Algunos datos no son válidos o son demasiado largos. Revísalos e intenta de nuevo."


def create_account(name, email, password, role=None):
    """Creates an account from the environment, only if its email and password are set."""
    if not (email and password):
        return
    try:
        upsert_user(name, email.strip().lower(), encrypt_password(password), role)
    except psycopg.Error as error:
        # If the database does not answer, the API starts anyway
        print(f"Could not create the account {email}: {error}")


def create_test_account():
    """The professor's test account (a normal traveller)."""
    create_account(config.TEST_ACCOUNT_NAME, config.TEST_ACCOUNT_EMAIL, config.TEST_ACCOUNT_PASSWORD)


def create_admin_account():
    """The terminal admin account."""
    create_account(config.ADMIN_ACCOUNT_NAME, config.ADMIN_ACCOUNT_EMAIL, config.ADMIN_ACCOUNT_PASSWORD, ROLE_ADMIN)


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
    create_admin_account()
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
    allow_methods=["GET", "POST"],  # changes use POST too, so no other method is needed
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
app.include_router(admin.router)
