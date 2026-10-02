from servicios.cargar_datos import cargar_grafo

grafo = cargar_grafo()
matriz = grafo.matriz_de_tiempos()

print("GRAFO")
grafo.mostrar()

print()
print("MATRIZ DE TIEMPOS (minutos)")
encabezado = "".ljust(10)
for j in range(grafo.cantidad):
    encabezado += grafo.buscar_por_indice(j).nombre[:7].rjust(8)
print(encabezado)

for i in range(grafo.cantidad):
    linea = grafo.buscar_por_indice(i).nombre.ljust(10)
    for j in range(grafo.cantidad):
        valor = matriz.obtener(i, j)
        if valor is None:
            linea += "—".rjust(8)
        else:
            linea += str(valor).rjust(8)
    print(linea)

print()
print("Pasto → Cali:", matriz.obtener(0, 5), "minutos")