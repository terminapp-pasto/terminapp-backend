"""Pila (LIFO) con nodos enlazados.

El último que entra es el primero que sale. En TerminAPP funciona como
registro para deshacer: al reservar varios asientos se apila cada uno; si
alguno ya estaba ocupado, se desapilan y se liberan en orden inverso, para que
no quede una compra a medias.
"""


class NodoPila:
    def __init__(self, dato):
        self.dato = dato
        self.debajo = None


class Pila:
    def __init__(self):
        self.cima = None
        self.cantidad = 0

    def esta_vacia(self):
        return self.cima is None

    def apilar(self, dato):
        """Pone encima. O(1)."""
        nuevo = NodoPila(dato)
        nuevo.debajo = self.cima
        self.cima = nuevo
        self.cantidad += 1

    def desapilar(self):
        """Saca y devuelve el de encima. O(1)."""
        if self.cima is None:
            return None
        dato = self.cima.dato
        self.cima = self.cima.debajo
        self.cantidad -= 1
        return dato

    def ver_cima(self):
        return None if self.cima is None else self.cima.dato
