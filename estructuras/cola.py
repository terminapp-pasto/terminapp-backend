"""Cola (FIFO) con nodos enlazados.

El primero que entra es el primero que sale. En TerminAPP guarda las reservas
pendientes por orden de llegada: la más antigua queda al frente, así basta con
mirar el frente para saber si alguna reserva ya venció.
"""


class NodoCola:
    def __init__(self, dato):
        self.dato = dato
        self.siguiente = None


class Cola:
    def __init__(self):
        self.frente = None
        self.final = None
        self.cantidad = 0

    def esta_vacia(self):
        return self.frente is None

    def encolar(self, dato):
        """Agrega al final. O(1)."""
        nuevo = NodoCola(dato)
        if self.final is None:
            self.frente = nuevo
        else:
            self.final.siguiente = nuevo
        self.final = nuevo
        self.cantidad += 1

    def desencolar(self):
        """Saca y devuelve el del frente. O(1)."""
        if self.frente is None:
            return None
        dato = self.frente.dato
        self.frente = self.frente.siguiente
        if self.frente is None:
            self.final = None
        self.cantidad -= 1
        return dato

    def ver_frente(self):
        """Mira el del frente sin sacarlo. O(1)."""
        return None if self.frente is None else self.frente.dato
