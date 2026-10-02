from servicios.cargar_datos import cargar_jerarquia

arbol = cargar_jerarquia()
arbol.mostrar()

print()
print("Rutas de TRANSIPIALES:")
empresa = arbol.raiz.buscar_hijo("TRANSIPIALES")
ruta = empresa.primer_hijo
while ruta is not None:
    print("  ", ruta.nombre)
    ruta = ruta.siguiente_hermano