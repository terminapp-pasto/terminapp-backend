"""Tabla hash con encadenamiento.

La tabla es un arreglo de tamaño fijo de "cubetas". Cada clave pasa por una
función hash propia que dice en qué cubeta va, así se encuentra en O(1) en
promedio sin recorrer todo. Si dos claves caen en la misma cubeta (colisión),
se encadenan en una lista enlazada de nodos propios. Cuando la tabla se llena
más del 75 %, se duplica el tamaño y se reubican las claves (rehash).
"""

FACTOR_DE_CARGA_MAXIMO = 0.75


class NodoHash:
    def __init__(self, clave, valor):
        self.clave = clave
        self.valor = valor
        self.siguiente = None


class TablaHash:
    def __init__(self, capacidad=16):
        self.capacidad = capacidad
        # El arreglo de cubetas es solo memoria de tamaño fijo, como en C:
        # nunca crece con append; todos los datos viven en nodos NodoHash.
        self.cubetas = [None] * capacidad
        self.cantidad = 0

    def _hash(self, clave):
        """Hash polinómico propio sobre los caracteres de la clave (no usa hash() de Python)."""
        texto = str(clave)
        valor = 0
        for caracter in texto:
            valor = (valor * 31 + ord(caracter)) % 1_000_000_007
        return valor % self.capacidad

    def insertar(self, clave, valor):
        """Agrega la clave o actualiza su valor si ya existe. O(1) promedio."""
        indice = self._hash(clave)
        nodo = self.cubetas[indice]
        while nodo is not None:
            if nodo.clave == clave:
                nodo.valor = valor
                return
            nodo = nodo.siguiente

        nuevo = NodoHash(clave, valor)
        nuevo.siguiente = self.cubetas[indice]
        self.cubetas[indice] = nuevo
        self.cantidad += 1

        if self.cantidad / self.capacidad > FACTOR_DE_CARGA_MAXIMO:
            self._redimensionar()

    def obtener(self, clave, por_defecto=None):
        """Devuelve el valor de la clave. O(1) promedio."""
        nodo = self.cubetas[self._hash(clave)]
        while nodo is not None:
            if nodo.clave == clave:
                return nodo.valor
            nodo = nodo.siguiente
        return por_defecto

    def contiene(self, clave):
        nodo = self.cubetas[self._hash(clave)]
        while nodo is not None:
            if nodo.clave == clave:
                return True
            nodo = nodo.siguiente
        return False

    def eliminar(self, clave):
        """Quita la clave. Devuelve True si estaba. O(1) promedio."""
        indice = self._hash(clave)
        anterior = None
        nodo = self.cubetas[indice]
        while nodo is not None:
            if nodo.clave == clave:
                if anterior is None:
                    self.cubetas[indice] = nodo.siguiente
                else:
                    anterior.siguiente = nodo.siguiente
                self.cantidad -= 1
                return True
            anterior = nodo
            nodo = nodo.siguiente
        return False

    def recorrer(self, visitar):
        """Llama visitar(clave, valor) por cada elemento. O(n + capacidad)."""
        for indice in range(self.capacidad):
            nodo = self.cubetas[indice]
            while nodo is not None:
                visitar(nodo.clave, nodo.valor)
                nodo = nodo.siguiente

    def _redimensionar(self):
        """Duplica la capacidad y vuelve a ubicar cada nodo en su nueva cubeta."""
        viejas = self.cubetas
        capacidad_vieja = self.capacidad
        self.capacidad *= 2
        self.cubetas = [None] * self.capacidad
        for indice in range(capacidad_vieja):
            nodo = viejas[indice]
            while nodo is not None:
                siguiente = nodo.siguiente
                nuevo_indice = self._hash(nodo.clave)
                nodo.siguiente = self.cubetas[nuevo_indice]
                self.cubetas[nuevo_indice] = nodo
                nodo = siguiente
