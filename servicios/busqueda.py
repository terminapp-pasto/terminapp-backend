from estructuras.avl import a_texto
from estructuras.heap import Heap
from servicios.cargar_datos import cargar_grafo, cargar_horarios


def buscar_salidas(origen, destino, desde=0, ordenar_por="hora"):
    grafo = cargar_grafo()
    vertice = grafo.buscar_vertice(origen)
    if vertice is None or grafo.buscar_vertice(destino) is None:
        return None

    arbol = cargar_horarios(destino)
    heap = Heap()

    def agregar(nodo):
        if vertice.buscar_arista(nodo.ruta_id) is None:
            return
        clave = nodo.precio * 1440 + nodo.minutos if ordenar_por == "precio" else nodo.minutos  
        heap.insertar(clave, nodo)

    arbol.recorrer_desde(desde, agregar)

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
            "cupos": salida.cupos,
        })
    return resultados   