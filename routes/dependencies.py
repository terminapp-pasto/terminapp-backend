"""Pieces shared by several routes: current user and date checks."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from authentication.tokens import TokenError, decode_token
from services.dates import InvalidDateError, parse_date, parse_travel_date
from services.users import find_user_by_id

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
