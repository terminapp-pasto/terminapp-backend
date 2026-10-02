from estructuras.avl import a_texto
from estructuras.heap import Heap
from servicios.cargar_datos import cargar_horarios

arbol = cargar_horarios("Cali")
heap = Heap()


def agregar_al_heap(nodo):
    heap.insertar(nodo.precio, nodo)


arbol.recorrer_desde(0, agregar_al_heap)

print("Salidas en el heap:", heap.cantidad)
print("La más barata está en la raíz:", f"${heap.raiz.clave:,}")

print()
print("Salidas a Cali, de la más barata a la más cara:")
while not heap.esta_vacio():
    salida = heap.extraer_minimo()
    print(f"  ${salida.precio:,}   sale {a_texto(salida.minutos)}")