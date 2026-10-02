from estructuras.avl import a_texto
from servicios.cargar_datos import cargar_horarios


def imprimir(nodo):
    print(f"  {a_texto(nodo.minutos)}   ${nodo.precio:,}   ({nodo.cupos} cupos)")


arbol = cargar_horarios("Tumaco")

print("Salidas cargadas:", arbol.cantidad)
print("Altura del árbol:", arbol.raiz.altura)
print("Raíz del árbol:", a_texto(arbol.raiz.minutos))

print()
print("Todas las salidas a Tumaco:")
arbol.recorrer_desde(0, imprimir)

print()
print("Salidas a Tumaco desde las 09:00:")
arbol.recorrer_desde(9 * 60, imprimir)