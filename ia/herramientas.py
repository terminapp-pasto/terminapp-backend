"""Herramientas que la IA puede pedirle al backend.

La IA no busca ni inventa horarios: solo decide qué herramienta usar y con qué
datos. Cada herramienta llama al motor de búsqueda, que trabaja con el grafo,
el árbol AVL y el heap.
"""

from servicios.busqueda import buscar_salidas
from servicios.compra import ErrorCompra, fecha_de_venta
from servicios.cargar_datos import cargar_grafo

ORIGEN = "Pasto"

# Descripción de cada herramienta en el formato que entiende Gemini.
DECLARACIONES = [
    {
        "name": "buscar_pasajes",
        "description": (
            "Busca las salidas de bus desde la Terminal de Pasto hacia un destino en un día, "
            "a partir de una hora, ordenadas por hora de salida o por precio, con los cupos libres de ese día. "
            "Úsala siempre que el usuario pregunte por pasajes, horarios o precios."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destino": {
                    "type": "string",
                    "description": "Municipio de destino, por ejemplo Cali, Ipiales o Sandoná.",
                },
                "fecha": {
                    "type": "string",
                    "description": "Día del viaje en formato AAAA-MM-DD. Si el usuario no dice el día, usa la fecha de hoy.",
                },
                "desde": {
                    "type": "string",
                    "description": "Hora mínima de salida en formato HH:MM de 24 horas. Usa 00:00 si el usuario no dice una hora.",
                },
                "ordenar_por": {
                    "type": "string",
                    "enum": ["hora", "precio"],
                    "description": "hora para ordenar por hora de salida, precio para ordenar del más barato al más caro.",
                },
            },
            "required": ["destino"],
        },
    },
    {
        "name": "listar_destinos",
        "description": "Devuelve los municipios a los que salen buses desde la Terminal de Pasto.",
    },
]


def buscar_pasajes(destino, desde="00:00", ordenar_por="hora", fecha=""):
    try:
        dia = fecha_de_venta(fecha)
    except ErrorCompra as error:
        return {"error": error.mensaje}
    try:
        horas, minutos = desde.split(":")
        desde_minutos = int(horas) * 60 + int(minutos)
    except (ValueError, AttributeError):
        return {"error": "La hora debe tener el formato HH:MM"}

    if ordenar_por not in ("hora", "precio"):
        ordenar_por = "hora"

    resultado = {"fecha": dia.isoformat()}
    salidas = buscar_salidas(ORIGEN, destino, desde_minutos, ordenar_por, dia)
    if salidas is None:
        # puede ser un error de escritura: "bodota" -> Bogotá
        parecido = cargar_grafo().buscar_parecido(destino)
        if parecido is not None and parecido.nombre != ORIGEN:
            salidas = buscar_salidas(ORIGEN, parecido.nombre, desde_minutos, ordenar_por, dia)
            resultado["nota"] = f'El usuario escribió "{destino}"; se entendió como {parecido.nombre}.'
    if salidas is None:
        return {
            "error": f"No hay rutas desde {ORIGEN} hacia {destino}.",
            "destinos_disponibles": listar_destinos()["destinos"],
        }
    resultado.update({"cantidad": len(salidas), "salidas": salidas})
    return resultado


def listar_destinos():
    grafo = cargar_grafo()
    vertice = grafo.buscar_vertice(ORIGEN)
    destinos = []
    arista = vertice.primera_arista if vertice is not None else None
    while arista is not None:
        if arista.destino not in destinos:
            destinos.append(arista.destino)
        arista = arista.siguiente
    return {"origen": ORIGEN, "destinos": destinos}


def ejecutar(nombre, argumentos):
    """Ejecuta la herramienta que pidió la IA y devuelve su resultado."""
    try:
        if nombre == "buscar_pasajes":
            return buscar_pasajes(
                destino=str(argumentos.get("destino", "")),
                desde=str(argumentos.get("desde", "00:00")),
                ordenar_por=str(argumentos.get("ordenar_por", "hora")),
                fecha=str(argumentos.get("fecha", "")),
            )
        if nombre == "listar_destinos":
            return listar_destinos()
        return {"error": f"No existe la herramienta {nombre}"}
    except Exception:
        return {"error": "No se pudo consultar la base de datos en este momento"}
