import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI

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