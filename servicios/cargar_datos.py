import os

import psycopg
from dotenv import load_dotenv

from estructuras.grafo import Grafo

load_dotenv()

CONSULTA_RUTAS = """
    SELECT r.id, o.nombre, d.nombre, r.duracion_min, e.nombre
    FROM rutas r
    JOIN destinos o ON o.id = r.origen_id
    JOIN destinos d ON d.id = r.destino_id
    JOIN empresas e ON e.id = r.empresa_id
    ORDER BY r.id;
"""


def cargar_grafo():
    grafo = Grafo()
    with psycopg.connect(os.getenv("DATABASE_URL")) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(CONSULTA_RUTAS)
            for ruta_id, origen, destino, duracion, empresa in cursor:
                grafo.agregar_ruta(origen, destino, duracion, empresa, ruta_id)
    return grafo    