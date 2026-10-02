from estructuras.matriz import Matriz   

class Arista:
    def __init__(self, destino, peso, empresa, ruta_id):
        self.destino = destino
        self.peso = peso
        self.empresa = empresa
        self.ruta_id = ruta_id
        self.siguiente = None

class Vertice:
    def __init__(self, nombre, indice):
        self.nombre = nombre
        self.indice = indice
        self.primera_arista = None
        self.siguiente = None

    def agregar_arista(self, arista):
        arista.siguiente = self.primera_arista
        self.primera_arista = arista    

    def buscar_arista(self, ruta_id):
        arista = self.primera_arista
        while arista is not None:
            if arista.ruta_id == ruta_id:
                return arista
            arista = arista.siguiente
        return None

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
        nuevo = Vertice(nombre, self.cantidad)
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

    def buscar_por_indice(self, indice):
        actual = self.primer_vertice    
        while actual is not None:
            if actual.indice == indice:
                return actual
            actual = actual.siguiente
        return None

    def matriz_de_tiempos(self):
        matriz = Matriz(self.cantidad, self.cantidad)
        vertice = self.primer_vertice
        while vertice is not None:
            matriz.asignar(vertice.indice, vertice.indice, 0)
            arista = vertice.primera_arista
            while arista is not None:
                destino = self.buscar_vertice(arista.destino)
                actual = matriz.obtener(vertice.indice, destino.indice)
                if actual is None or arista.peso < actual:
                    matriz.asignar(vertice.indice, destino.indice, arista.peso)
                arista = arista.siguiente
            vertice = vertice.siguiente
        return matriz   
     
    
                      