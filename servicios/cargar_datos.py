import os

import psycopg
from dotenv import load_dotenv

from estructuras.grafo import Grafo
from estructuras.avl import ArbolAVL, a_minutos, a_texto
from estructuras.nario import ArbolNario, NodoNario 

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

CONSULTA_HORARIOS = """
    SELECT h.id, h.ruta_id, h.hora_salida, h.precio, h.cupos
    FROM horarios h
    JOIN rutas r ON r.id = h.ruta_id
    JOIN destinos d ON d.id = r.destino_id
    WHERE d.nombre = %s
    ORDER BY h.hora_salida;
"""


def cargar_horarios(destino):
    arbol = ArbolAVL()
    with psycopg.connect(os.getenv("DATABASE_URL")) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(CONSULTA_HORARIOS, (destino,))
            for horario_id, ruta_id, hora, precio, cupos in cursor:
                arbol.insertar(a_minutos(hora), horario_id, ruta_id, precio, cupos)
    return arbol    

CONSULTA_JERARQUIA = """
    SELECT e.nombre, o.nombre, d.nombre, h.id, h.hora_salida, h.precio
    FROM horarios h
    JOIN rutas r ON r.id = h.ruta_id
    JOIN empresas e ON e.id = r.empresa_id
    JOIN destinos o ON o.id = r.origen_id
    JOIN destinos d ON d.id = r.destino_id
    ORDER BY e.nombre, d.nombre, h.hora_salida;
"""


def cargar_jerarquia():
    arbol = ArbolNario("Terminal de Pasto")
    with psycopg.connect(os.getenv("DATABASE_URL")) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(CONSULTA_JERARQUIA)
            for empresa, origen, destino, horario_id, hora, precio in cursor:
                nodo_empresa = arbol.raiz.obtener_hijo(empresa)
                nodo_ruta = nodo_empresa.obtener_hijo(f"{origen} → {destino}")
                texto = f"{a_texto(a_minutos(hora))}  ${precio:,}"
                nodo_ruta.agregar_hijo(NodoNario(texto, horario_id))
    return arbol    