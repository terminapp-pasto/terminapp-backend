"""Pieces shared by several routes: current user and date checks."""

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from authentication.tokens import TokenError, decode_token
from services.dates import InvalidDateError, parse_date, parse_travel_date
from services.rate_limit import (
    CHAT_LIMITER, LOGIN_LIMITER, PAYMENT_LIMITER, PURCHASE_LIMITER, REGISTER_LIMITER, RateLimiter,
)
from services.users import ROLE_ADMIN, ROLE_COMPANY, find_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    """Protects a route: requires a valid token and returns the user who owns it."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión")
    try:
        claims = decode_token(credentials.credentials)
    except TokenError as error:
        raise HTTPException(status_code=401, detail=str(error))

    user = find_user_by_id(int(claims["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="El usuario ya no existe")
    return user


def require_date(text):
    """Required YYYY-MM-DD date; responds 400 if it is invalid."""
    try:
        return parse_date(text)
    except InvalidDateError as error:
        raise HTTPException(status_code=400, detail=str(error))


def require_travel_date(text):
    """Travel date (empty = today) inside the sales window; responds 400 if it is invalid."""
    try:
        return parse_travel_date(text)
    except InvalidDateError as error:
        raise HTTPException(status_code=400, detail=str(error))


def client_address(request: Request):
    """The visitor's IP. On Render the request arrives through a proxy, which sends it
    in X-Forwarded-For (the first address is the real client)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def build_rate_limit(limiter: RateLimiter):
    """Creates a route dependency that answers 429 when a client goes over the limit."""

    def check_rate_limit(request: Request):
        client = client_address(request)
        if not limiter.allow(client):
            wait = limiter.seconds_until_allowed(client)
            raise HTTPException(
                status_code=429,
                detail=f"Hiciste demasiados intentos seguidos. Espera {wait} segundos e intenta de nuevo.",
                headers={"Retry-After": str(wait)},
            )

    return check_rate_limit


limit_login = build_rate_limit(LOGIN_LIMITER)
limit_register = build_rate_limit(REGISTER_LIMITER)
limit_chat = build_rate_limit(CHAT_LIMITER)
limit_purchases = build_rate_limit(PURCHASE_LIMITER)
limit_payments = build_rate_limit(PAYMENT_LIMITER)


def require_staff(user: dict = Depends(get_current_user)):
    """Protects the admin panel: the terminal admin or a bus company employee."""
    if user["role"] == ROLE_ADMIN:
        return user
    if user["role"] == ROLE_COMPANY and user["company_id"] is not None:
        return user
    raise HTTPException(status_code=403, detail="Esta sección es solo para el administrador y las empresas")


def require_admin(user: dict = Depends(get_current_user)):
    """Only the terminal admin."""
    if user["role"] != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Solo el administrador de la terminal puede hacer esto")
    return user


def company_scope(user):
    """None for the admin (sees every company); the company id for a company employee."""
    return None if user["role"] == ROLE_ADMIN else user["company_id"]
