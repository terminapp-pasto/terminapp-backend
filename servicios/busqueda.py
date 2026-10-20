from datetime import datetime

from estructuras.avl import a_texto
from estructuras.heap import Heap
from servicios.cargar_datos import cargar_grafo, cargar_horarios
from servicios.compra import ZONA_COLOMBIA, hoy_en_colombia, ocupados_por_horario


def buscar_salidas(origen, destino, desde=0, ordenar_por="hora", fecha=None):
    """Salidas de un día (hoy si no se dice) desde una hora, con los cupos libres reales."""
    fecha = fecha or hoy_en_colombia()
    if fecha == hoy_en_colombia():
        ahora = datetime.now(ZONA_COLOMBIA)
        desde = max(desde, ahora.hour * 60 + ahora.minute + 1)  # no mostrar buses que ya salieron

    grafo = cargar_grafo()
    vertice = grafo.buscar_vertice(origen)
    vertice_destino = grafo.buscar_vertice(destino)
    if vertice is None or vertice_destino is None:
        return None
    origen = vertice.nombre
    destino = vertice_destino.nombre

    arbol = cargar_horarios(destino)
    heap = Heap()

    def agregar(nodo):
        if vertice.buscar_arista(nodo.ruta_id) is None:
            return
        clave = nodo.precio * 1440 + nodo.minutos if ordenar_por == "precio" else nodo.minutos  
        heap.insertar(clave, nodo)

    arbol.recorrer_desde(desde, agregar)

    ocupados = ocupados_por_horario(fecha) if not heap.esta_vacio() else None
    resultados = []
    while not heap.esta_vacio():
        salida = heap.extraer_minimo()
        arista = vertice.buscar_arista(salida.ruta_id)
        resultados.append({
            "horario_id": salida.horario_id,
            "empresa": arista.empresa,
            "origen": origen,
            "destino": destino,
            "hora_salida": a_texto(salida.minutos),
            "duracion_min": arista.peso,
            "precio": salida.precio,
            "fecha": fecha.isoformat(),
            "cupos": salida.cupos - ocupados.obtener(salida.horario_id, 0),
        })
    return resultados   