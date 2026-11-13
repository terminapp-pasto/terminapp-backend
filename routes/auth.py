"""Account routes: register, login and user data."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from authentication.tokens import create_token
from authentication.utilities import encrypt_password, verify_password
from routes.dependencies import get_current_user, limit_login, limit_register
from services.users import create_user, find_user_by_email
from services.validation import (
    EMAIL_MAX_LENGTH, EMAIL_RULE, NAME_MAX_LENGTH, NAME_RULE, PASSWORD_MAX_LENGTH, PASSWORD_RULE,
    is_valid_email, is_valid_name, is_valid_password, normalize_spaces,
)

router = APIRouter(tags=["Account"])


class RegisterRequest(BaseModel):
    # max_length here stops huge texts before processing them; the detailed rules come below
    name: str = Field(..., max_length=NAME_MAX_LENGTH * 2)
    email: str = Field(..., max_length=EMAIL_MAX_LENGTH * 2)
    password: str = Field(..., max_length=PASSWORD_MAX_LENGTH * 2)


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=EMAIL_MAX_LENGTH * 2)
    password: str = Field(..., max_length=PASSWORD_MAX_LENGTH * 2)


def build_session_response(user):
    public_user = {key: user[key] for key in ("id", "name", "email", "role", "company_id", "company")}
    return {"token": create_token(user["id"], user["name"]), "user": public_user}


@router.post(
    "/register",
    status_code=201,
    summary="Creates an account and returns a token",
    dependencies=[Depends(limit_register)],
)
def register(request: RegisterRequest):
    name = normalize_spaces(request.name)
    email = request.email.strip().lower()

    if not is_valid_name(name):
        raise HTTPException(status_code=400, detail=NAME_RULE)
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail=EMAIL_RULE)
    if not is_valid_password(request.password):
        raise HTTPException(status_code=400, detail=PASSWORD_RULE)

    user = create_user(name, email, encrypt_password(request.password))
    if user is None:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    return build_session_response(user)


@router.post(
    "/login",
    summary="Logs in and returns a 24-hour JWT token",
    dependencies=[Depends(limit_login)],
)
def login(request: LoginRequest):
    user = find_user_by_email(request.email.strip().lower())
    # Same message for a wrong email or password, so we never reveal which emails exist
    if user is None or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    return build_session_response(user)


@router.get("/me", summary="🔒 Data of the user who owns the token")
def me(user: dict = Depends(get_current_user)):
    return user
