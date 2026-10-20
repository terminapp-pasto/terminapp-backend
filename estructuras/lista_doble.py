"""Lista doblemente enlazada.

Cada nodo conoce al anterior y al siguiente, así se puede recorrer en los dos
sentidos. En TerminAPP guarda el historial de tiquetes del usuario: de la
cabeza hacia la cola son los más recientes primero, y al revés los más
antiguos primero, sin tener que volver a ordenar.
"""


class NodoDoble:
    def __init__(self, dato):
        self.dato = dato
        self.anterior = None
        self.siguiente = None


class ListaDoble:
    def __init__(self):
        self.cabeza = None
        self.cola = None
        self.cantidad = 0

    def esta_vacia(self):
        return self.cabeza is None

    def agregar_al_final(self, dato):
        """O(1)."""
        nuevo = NodoDoble(dato)
        if self.cola is None:
            self.cabeza = nuevo
        else:
            nuevo.anterior = self.cola
            self.cola.siguiente = nuevo
        self.cola = nuevo
        self.cantidad += 1
        return nuevo

    def agregar_al_inicio(self, dato):
        """O(1)."""
        nuevo = NodoDoble(dato)
        if self.cabeza is None:
            self.cola = nuevo
        else:
            nuevo.siguiente = self.cabeza
            self.cabeza.anterior = nuevo
        self.cabeza = nuevo
        self.cantidad += 1
        return nuevo

    def eliminar_nodo(self, nodo):
        """Quita un nodo que ya se tiene en la mano. O(1)."""
        if nodo.anterior is None:
            self.cabeza = nodo.siguiente
        else:
            nodo.anterior.siguiente = nodo.siguiente
        if nodo.siguiente is None:
            self.cola = nodo.anterior
        else:
            nodo.siguiente.anterior = nodo.anterior
        nodo.anterior = nodo.siguiente = None
        self.cantidad -= 1

    def recorrer_adelante(self, visitar):
        """De la cabeza a la cola. O(n)."""
        nodo = self.cabeza
        while nodo is not None:
            visitar(nodo.dato)
            nodo = nodo.siguiente

    def recorrer_atras(self, visitar):
        """De la cola a la cabeza. O(n)."""
        nodo = self.cola
        while nodo is not None:
            visitar(nodo.dato)
            nodo = nodo.anterior
