class NodoAVL:
    def __init__(self, minutos, horario_id, ruta_id, precio, cupos):
        self.minutos = minutos
        self.horario_id = horario_id
        self.ruta_id = ruta_id
        self.precio = precio
        self.cupos = cupos
        self.izquierdo = None
        self.derecho = None
        self.altura = 1

class ArbolAVL:
    def __init__(self):
        self.raiz = None
        self.cantidad = 0

    def _altura(self, nodo):
        if nodo is None:
            return 0
        return nodo.altura

    def _actualizar_altura(self, nodo):
        nodo.altura = 1 + max(self._altura(nodo.izquierdo), self._altura(nodo.derecho))

    def _equilibrio(self, nodo):
        return self._altura(nodo.izquierdo) - self._altura(nodo.derecho)    

    def _rotar_derecha(self, nodo):
        hijo = nodo.izquierdo
        nieto = hijo.derecho
        hijo.derecho = nodo
        nodo.izquierdo = nieto
        self._actualizar_altura(nodo)
        self._actualizar_altura(hijo)
        return hijo

    def _rotar_izquierda(self, nodo):
        hijo = nodo.derecho
        nieto = hijo.izquierdo
        hijo.izquierdo = nodo
        nodo.derecho = nieto
        self._actualizar_altura(nodo)
        self._actualizar_altura(hijo)
        return hijo

    def insertar(self, minutos, horario_id, ruta_id, precio, cupos):
        nuevo = NodoAVL(minutos, horario_id, ruta_id, precio, cupos)
        self.raiz = self._insertar(self.raiz, nuevo)
        self.cantidad += 1

    def _insertar(self, nodo, nuevo):
        if nodo is None:
            return nuevo
        if nuevo.minutos < nodo.minutos:
            nodo.izquierdo = self._insertar(nodo.izquierdo, nuevo)
        else:
            nodo.derecho = self._insertar(nodo.derecho, nuevo)
        self._actualizar_altura(nodo)
        return self._balancear(nodo)

    def _balancear(self, nodo):
        equilibrio = self._equilibrio(nodo)
        if equilibrio > 1:
            if self._equilibrio(nodo.izquierdo) < 0:
                nodo.izquierdo = self._rotar_izquierda(nodo.izquierdo)
            return self._rotar_derecha(nodo)
        if equilibrio < -1:
            if self._equilibrio(nodo.derecho) > 0:
                nodo.derecho = self._rotar_derecha(nodo.derecho)
            return self._rotar_izquierda(nodo)
        return nodo 

    def recorrer_desde(self, desde, accion):
        self._recorrer_desde(self.raiz, desde, accion)

    def _recorrer_desde(self, nodo, desde, accion):
        if nodo is None:
            return
        if nodo.minutos >= desde:
            self._recorrer_desde(nodo.izquierdo, desde, accion)
            accion(nodo)
        self._recorrer_desde(nodo.derecho, desde, accion)

def a_minutos(hora):
    return hora.hour * 60 + hora.minute


def a_texto(minutos):
    return f"{minutos // 60:02d}:{minutos % 60:02d}"