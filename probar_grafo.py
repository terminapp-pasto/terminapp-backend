from servicios.cargar_datos import cargar_grafo

grafo = cargar_grafo()

print("Municipios en el grafo:", grafo.cantidad)
grafo.mostrar()