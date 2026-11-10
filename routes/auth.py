"""Rutas de la cuenta: registro, inicio de sesión y datos del usuario."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from authentication.tokens import create_token
from authentication.utilities import encrypt_password, verify_password
from routes.dependencies import get_current_user
from services.users import create_user, find_user_by_email
from services.validation import (
    EMAIL_MAX_LENGTH, EMAIL_RULE, NAME_MAX_LENGTH, NAME_RULE, PASSWORD_MAX_LENGTH, PASSWORD_RULE,
    is_valid_email, is_valid_name, is_valid_password, normalize_spaces,
)

router = APIRouter(tags=["Cuenta"])


class RegisterRequest(BaseModel):
    # max_length aquí corta textos gigantes antes de procesarlos; las reglas finas van abajo
    name: str = Field(..., max_length=NAME_MAX_LENGTH * 2)
    email: str = Field(..., max_length=EMAIL_MAX_LENGTH * 2)
    password: str = Field(..., max_length=PASSWORD_MAX_LENGTH * 2)


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=EMAIL_MAX_LENGTH * 2)
    password: str = Field(..., max_length=PASSWORD_MAX_LENGTH * 2)


def build_session_response(user):
    public_user = {"id": user["id"], "name": user["name"], "email": user["email"]}
    return {"token": create_token(user["id"], user["name"]), "user": public_user}


@router.post("/register", status_code=201, summary="Crea una cuenta y devuelve un token")
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


@router.post("/login", summary="Inicia sesión y devuelve un token JWT de 24 horas")
def login(request: LoginRequest):
    user = find_user_by_email(request.email.strip().lower())
    # El mismo mensaje para correo o contraseña incorrectos, para no revelar qué correos existen
    if user is None or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    return build_session_response(user)


@router.get("/me", summary="🔒 Datos del usuario dueño del token")
def me(user: dict = Depends(get_current_user)):
    return user
