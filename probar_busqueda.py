from servicios.busqueda import buscar_salidas

resultados = buscar_salidas("Pasto", "Cali", 20 * 60, "precio")

print("Pasto → Cali desde las 20:00, por precio:")
for r in resultados:
    print(f"  {r['hora_salida']}  {r['empresa']:<20} ${r['precio']:,}  {r['duracion_min']} min")