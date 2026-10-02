class NodoNario:
    def __init__(self, nombre, dato=None):
        self.nombre = nombre
        self.dato = dato
        self.primer_hijo = None
        self.siguiente_hermano = None

    def agregar_hijo(self, hijo):
        if self.primer_hijo is None:
            self.primer_hijo = hijo
            return
        actual = self.primer_hijo
        while actual.siguiente_hermano is not None:
            actual = actual.siguiente_hermano
        actual.siguiente_hermano = hijo

    def buscar_hijo(self, nombre):
        actual = self.primer_hijo
        while actual is not None:
            if actual.nombre == nombre:
                return actual
            actual = actual.siguiente_hermano
        return None

    def obtener_hijo(self, nombre):
        hijo = self.buscar_hijo(nombre)
        if hijo is None:
            hijo = NodoNario(nombre)
            self.agregar_hijo(hijo)
        return hijo


class ArbolNario:
    def __init__(self, nombre_raiz):
        self.raiz = NodoNario(nombre_raiz)

    def mostrar(self):
        self._mostrar(self.raiz, 0)

    def _mostrar(self, nodo, nivel):
        print("    " * nivel + nodo.nombre)
        hijo = nodo.primer_hijo
        while hijo is not None:
            self._mostrar(hijo, nivel + 1)
            hijo = hijo.siguiente_hermano