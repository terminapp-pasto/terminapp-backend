import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from servicios.busqueda import buscar_salidas   

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="TerminAPP Backend")


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

    return {"origen": origen, "destino": destino, "cantidad": len(salidas), "salidas": salidas}