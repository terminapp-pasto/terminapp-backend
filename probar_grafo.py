from estructuras.grafo import Grafo

grafo = Grafo()

grafo.agregar_ruta("Pasto", "Ipiales", 100, "CONTINENTAL BUS", 1)
grafo.agregar_ruta("Pasto", "Ipiales", 100, "EXPRESO BOLIVARIANO", 2)
grafo.agregar_ruta("Pasto", "Sandoná", 135, "TRANSANDONA", 3)
grafo.agregar_ruta("Pasto", "Tumaco", 360, "TRANSIPIALES", 4)
grafo.agregar_ruta("Pasto", "Mocoa", 320, "TRANSIPIALES", 5)
grafo.agregar_ruta("Pasto", "Cali", 580, "EXPRESO BOLIVARIANO", 6)
grafo.agregar_ruta("Pasto", "Cali", 580, "TRANSIPIALES", 7)
grafo.agregar_ruta("Pasto", "Bogotá", 1100, "CONTINENTAL BUS", 8)

print("Municipios en el grafo:", grafo.cantidad)
grafo.mostrar()