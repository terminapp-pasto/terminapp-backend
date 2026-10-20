from estructuras.matriz import Matriz   

def normalizar(texto):
    texto = texto.strip().lower()
    texto = texto.replace("á", "a").replace("é", "e").replace("í", "i")
    texto = texto.replace("ó", "o").replace("ú", "u").replace("ü", "u")
    return texto

def distancia_de_edicion(a, b):
    """Cuántas letras hay que cambiar, quitar o poner para pasar de a a b (Levenshtein).
    Usa la matriz de nodos como tabla de programación dinámica: la celda (i, j)
    guarda la distancia entre las primeras i letras de a y las primeras j de b."""
    a, b = normalizar(a), normalizar(b)
    tabla = Matriz(len(a) + 1, len(b) + 1, 0)
    for i in range(len(a) + 1):
        tabla.asignar(i, 0, i)
    for j in range(len(b) + 1):
        tabla.asignar(0, j, j)
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cambio = 0 if a[i - 1] == b[j - 1] else 1
            tabla.asignar(i, j, min(
                tabla.obtener(i - 1, j) + 1,           # quitar una letra
                tabla.obtener(i, j - 1) + 1,           # poner una letra
                tabla.obtener(i - 1, j - 1) + cambio,  # cambiar una letra
            ))
    return tabla.obtener(len(a), len(b))


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
        buscado = normalizar(nombre)
        actual = self.primer_vertice
        while actual is not None:
            if normalizar(actual.nombre) == buscado:
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

    def buscar_parecido(self, nombre):
        """El municipio con el nombre más parecido, para corregir errores como "bodota".
        Solo acepta hasta 2 letras de diferencia (y no más de un tercio del nombre)."""
        mejor, menor = None, None
        vertice = self.primer_vertice
        while vertice is not None:
            distancia = distancia_de_edicion(nombre, vertice.nombre)
            if menor is None or distancia < menor:
                mejor, menor = vertice, distancia
            vertice = vertice.siguiente
        if mejor is None or menor > 2 or menor * 3 > len(normalizar(nombre)):
            return None
        return mejor

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
     
    
                      