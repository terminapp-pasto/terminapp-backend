class Arista:
    def __init__(self, destino, peso, empresa, ruta_id):
        self.destino = destino
        self.peso = peso
        self.empresa = empresa
        self.ruta_id = ruta_id
        self.siguiente = None

class Vertice:
    def __init__(self, nombre):
        self.nombre = nombre
        self.primera_arista = None
        self.siguiente = None

    def agregar_arista(self, arista):
        arista.siguiente = self.primera_arista
        self.primera_arista = arista      

class Grafo:
    def __init__(self):
        self.primer_vertice = None
        self.cantidad = 0

    def buscar_vertice(self, nombre):
        actual = self.primer_vertice
        while actual is not None:
            if actual.nombre == nombre:
                return actual
            actual = actual.siguiente
        return None

    def agregar_vertice(self, nombre):
        existente = self.buscar_vertice(nombre)
        if existente is not None:
            return existente
        nuevo = Vertice(nombre)
        nuevo.siguiente = self.primer_vertice
        self.primer_vertice = nuevo
        self.cantidad += 1
        return nuevo

    def agregar_ruta(self, origen, destino, peso, empresa, ruta_id):
        vertice_origen = self.agregar_vertice(origen)
        self.agregar_vertice(destino)
        arista = Arista(destino, peso, empresa, ruta_id)
        vertice_origen.agregar_arista(arista)    
        
    def mostrar(self):
        vertice = self.primer_vertice   
        while vertice is not None:
            texto = vertice.nombre + " →"   
            arista = vertice.primera_arista 
            if arista is None:
                texto += " (sin salidas)"
            while arista is not None:
                texto += f" [{arista.destino} {arista.peso} min {arista.empresa}]"
                arista = arista.siguiente
            print(texto)
            vertice = vertice.siguiente              