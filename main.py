import os

import psycopg
from dotenv import load_dotenv
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ia.gemini import ErrorIA
from ia.herramientas import listar_destinos
from ia.orquestador import responder
from servicios.busqueda import buscar_salidas

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
