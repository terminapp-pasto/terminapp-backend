"""Pila (LIFO) con nodos enlazados.

El último que entra es el primero que sale. En TerminAPP funciona como
registro para deshacer: al reservar varios asientos se apila cada uno; si
alguno ya estaba ocupado, se desapilan y se liberan en orden inverso, para que
no quede una compra a medias.
"""


class StackNode:
    def __init__(self, data):
        self.data = data
        self.below = None


class Stack:
    def __init__(self):
        self.top = None
        self.size = 0

    def is_empty(self):
        return self.top is None

    def push(self, data):
        """Pone encima. O(1)."""
        new_node = StackNode(data)
        new_node.below = self.top
        self.top = new_node
        self.size += 1

    def pop(self):
        """Saca y devuelve el de encima. O(1)."""
        if self.top is None:
            return None
        data = self.top.data
        self.top = self.top.below
        self.size -= 1
        return data

    def peek(self):
        return None if self.top is None else self.top.data
