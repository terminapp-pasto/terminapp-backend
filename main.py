import os
import re

import psycopg
from dotenv import load_dotenv
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from autenticacion.contrasenas import cifrar_contrasena, verificar_contrasena
from autenticacion.tokens import ErrorToken, crear_token, leer_token
from ia.gemini import ErrorIA
from ia.herramientas import listar_destinos
from ia.orquestador import responder
from servicios.busqueda import buscar_salidas
from servicios.usuarios import buscar_por_correo, buscar_por_id, crear_usuario

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="TerminAPP Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://terminapp-frontend.*\.vercel\.app|http://localhost:5173",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def inicio():
    return {"mensaje": "Hello World desde el backend de TerminAPP"}


@app.get("/salud")
def salud():
    with psycopg.connect(DATABASE_URL) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
    return {"base_de_datos": "conectada", "version": version}

@app.get("/buscar")
def buscar(destino: str, origen: str = "Pasto", desde: str = "00:00", ordenar_por: str = "hora"):
    try:
        horas, minutos = desde.split(":")
        desde_minutos = int(horas) * 60 + int(minutos)
    except ValueError:
        raise HTTPException(status_code=400, detail="La hora debe tener el formato HH:MM")

    salidas = buscar_salidas(origen, destino, desde_minutos, ordenar_por)
    if salidas is None:
        raise HTTPException(status_code=404, detail="No conozco ese origen o ese destino")

    nombre_destino = salidas[0]["destino"] if salidas else destino
    return {"origen": origen, "destino": nombre_destino, "cantidad": len(salidas), "salidas": salidas}


@app.get("/destinos")
def destinos():
    return listar_destinos()


class Mensaje(BaseModel):
    rol: Literal["usuario", "asistente"]
    texto: str


class PeticionChat(BaseModel):
    mensajes: list[Mensaje]


@app.post("/chat")
def chat(peticion: PeticionChat):
    if not peticion.mensajes:
        raise HTTPException(status_code=400, detail="Envía al menos un mensaje")
    try:
        return responder([mensaje.model_dump() for mensaje in peticion.mensajes])
    except ErrorIA as error:
        print("Error de la IA:", error)
        raise HTTPException(status_code=502, detail="El asistente no está disponible en este momento. Intenta de nuevo en unos segundos.")


# ---------------- Autenticación ----------------

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
esquema_token = HTTPBearer(auto_error=False)


class PeticionRegistro(BaseModel):
    nombre: str
    correo: str
    contrasena: str


class PeticionInicioSesion(BaseModel):
    correo: str
    contrasena: str


def respuesta_con_token(usuario):
    datos = {"id": usuario["id"], "nombre": usuario["nombre"], "correo": usuario["correo"]}
    return {"token": crear_token(usuario["id"], usuario["nombre"]), "usuario": datos}


def usuario_actual(credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_token)):
    """Protege una ruta: exige un token válido y devuelve el usuario dueño del token."""
    if credenciales is None:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión")
    try:
        datos = leer_token(credenciales.credentials)
    except ErrorToken as error:
        raise HTTPException(status_code=401, detail=str(error))

    usuario = buscar_por_id(int(datos["sub"]))
    if usuario is None:
        raise HTTPException(status_code=401, detail="El usuario ya no existe")
    return usuario


@app.post("/registro", status_code=201)
def registro(peticion: PeticionRegistro):
    nombre = peticion.nombre.strip()
    correo = peticion.correo.strip().lower()

    if len(nombre) < 2:
        raise HTTPException(status_code=400, detail="Escribe tu nombre")
    if not PATRON_CORREO.match(correo):
        raise HTTPException(status_code=400, detail="El correo no es válido")
    if len(peticion.contrasena) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres")

    usuario = crear_usuario(nombre, correo, cifrar_contrasena(peticion.contrasena))
    if usuario is None:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    return respuesta_con_token(usuario)


@app.post("/inicio-sesion")
def inicio_sesion(peticion: PeticionInicioSesion):
    usuario = buscar_por_correo(peticion.correo.strip().lower())
    # El mismo mensaje para correo o contraseña incorrectos, para no revelar qué correos existen
    if usuario is None or not verificar_contrasena(peticion.contrasena, usuario["password_hash"]):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    return respuesta_con_token(usuario)


@app.get("/yo")
def yo(usuario: dict = Depends(usuario_actual)):
    """Ruta protegida: devuelve los datos del usuario que inició sesión."""
    return usuario
