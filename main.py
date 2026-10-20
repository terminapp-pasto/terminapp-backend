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
from pagos.stripe_api import ErrorPago, consultar_sesion, crear_sesion_de_pago
from ia.herramientas import listar_destinos
from ia.orquestador import responder
from servicios import compra
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


# ---------------- Compra de pasajes ----------------

URL_FRONTEND = os.getenv("FRONTEND_URL", "https://terminapp-frontend.vercel.app").rstrip("/")


def error_de_compra(error):
    return HTTPException(status_code=error.codigo, detail=error.mensaje)


class Pasajero(BaseModel):
    nombre: str
    documento: str


class PeticionCompra(BaseModel):
    horario_id: int
    fecha: str
    asientos: list[int]
    pasajero: Pasajero


@app.get("/horarios/{horario_id}/asientos")
def asientos(horario_id: int, fecha: str):
    """Mapa de asientos de una salida en una fecha (AAAA-MM-DD)."""
    try:
        return compra.mapa_de_asientos(horario_id, compra.leer_fecha(fecha))
    except compra.ErrorCompra as error:
        raise error_de_compra(error)


@app.post("/compras", status_code=201)
def crear_compra(peticion: PeticionCompra, usuario: dict = Depends(usuario_actual)):
    """🔒 Aparta los asientos por 15 minutos mientras el usuario paga."""
    try:
        return compra.reservar(
            usuario["id"],
            peticion.horario_id,
            compra.leer_fecha(peticion.fecha),
            peticion.asientos,
            peticion.pasajero.nombre,
            peticion.pasajero.documento,
        )
    except compra.ErrorCompra as error:
        raise error_de_compra(error)


@app.post("/compras/{pago_id}/pagar")
def pagar(pago_id: int, usuario: dict = Depends(usuario_actual)):
    """🔒 Crea la página de pago de Stripe y devuelve su dirección."""
    try:
        datos = compra.datos_para_pagar(usuario["id"], pago_id)
        session_id, url = crear_sesion_de_pago(
            pago_id, datos["descripcion"], datos["precio"], datos["cantidad"], URL_FRONTEND
        )
        compra.marcar_pagando(usuario["id"], pago_id, session_id)
    except compra.ErrorCompra as error:
        raise error_de_compra(error)
    except ErrorPago as error:
        print("Error de Stripe:", error)
        raise HTTPException(status_code=502, detail="No se pudo abrir la página de pago. Intenta de nuevo.")
    return {"url": url}


@app.get("/compras/confirmar")
def confirmar(session_id: str, usuario: dict = Depends(usuario_actual)):
    """🔒 Al volver de Stripe, pregunta a Stripe si el pago se hizo y confirma los tiquetes."""
    try:
        pago_id, pagado = consultar_sesion(session_id)
        if not pagado:
            raise HTTPException(status_code=402, detail="El pago todavía no aparece como aprobado")
        estado = compra.marcar_pagado(usuario["id"], pago_id)
    except compra.ErrorCompra as error:
        raise error_de_compra(error)
    except ErrorPago as error:
        print("Error de Stripe:", error)
        raise HTTPException(status_code=502, detail="No se pudo confirmar el pago con Stripe. Intenta de nuevo.")
    return {"pago_id": pago_id, "estado": estado}


@app.post("/compras/{pago_id}/cancelar")
def cancelar_compra(pago_id: int, usuario: dict = Depends(usuario_actual)):
    """🔒 Cancela una compra que todavía no se ha pagado y libera los asientos."""
    try:
        return {"pago_id": pago_id, "estado": compra.cancelar(usuario["id"], pago_id)}
    except compra.ErrorCompra as error:
        raise error_de_compra(error)


@app.get("/mis-tiquetes")
def tiquetes(orden: Literal["recientes", "antiguos"] = "recientes", usuario: dict = Depends(usuario_actual)):
    """🔒 Historial de tiquetes del usuario (lista doblemente enlazada)."""
    return compra.mis_tiquetes(usuario["id"], orden)
