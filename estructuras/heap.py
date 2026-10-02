class NodoHeap:
    def __init__(self, clave, dato):
        self.clave = clave
        self.dato = dato
        self.izquierdo = None
        self.derecho = None
        self.padre = None


class Heap:
    def __init__(self):
        self.raiz = None
        self.cantidad = 0

    def esta_vacio(self):
        return self.cantidad == 0

    def _nodo_en(self, posicion):
        potencia = 1
        while potencia * 2 <= posicion:
            potencia *= 2
        nodo = self.raiz
        potencia //= 2
        while potencia >= 1:
            if (posicion // potencia) % 2 == 1:
                nodo = nodo.derecho
            else:
                nodo = nodo.izquierdo
            potencia //= 2
        return nodo

    def _intercambiar(self, a, b):
        a.clave, b.clave = b.clave, a.clave
        a.dato, b.dato = b.dato, a.dato

    def _subir(self, nodo):
        while nodo.padre is not None and nodo.clave < nodo.padre.clave:
            self._intercambiar(nodo, nodo.padre)
            nodo = nodo.padre

    def insertar(self, clave, dato):
        nuevo = NodoHeap(clave, dato)
        self.cantidad += 1
        if self.raiz is None:
            self.raiz = nuevo
            return
        padre = self._nodo_en(self.cantidad // 2)
        nuevo.padre = padre
        if padre.izquierdo is None:
            padre.izquierdo = nuevo
        else:
            padre.derecho = nuevo
        self._subir(nuevo)

    def _bajar(self, nodo):
        while True:
            menor = nodo
            if nodo.izquierdo is not None and nodo.izquierdo.clave < menor.clave:
                menor = nodo.izquierdo
            if nodo.derecho is not None and nodo.derecho.clave < menor.clave:
                menor = nodo.derecho
            if menor is nodo:
                return
            self._intercambiar(nodo, menor)
            nodo = menor

    def extraer_minimo(self):
        if self.raiz is None:
            return None
        dato = self.raiz.dato
        ultimo = self._nodo_en(self.cantidad)
        if ultimo is self.raiz:
            self.raiz = None
        else:
            self.raiz.clave = ultimo.clave
            self.raiz.dato = ultimo.dato
            padre = ultimo.padre
            if padre.derecho is ultimo:
                padre.derecho = None
            else:
                padre.izquierdo = None
            self._bajar(self.raiz)
        self.cantidad -= 1
        return dato 