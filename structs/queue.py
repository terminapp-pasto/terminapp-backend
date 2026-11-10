"""Cola (FIFO) con nodos enlazados.

El primero que entra es el primero que sale. En TerminAPP guarda las reservas
pendientes por orden de llegada: la más antigua queda al frente, así basta con
mirar el frente para saber si alguna reserva ya venció.
"""


class QueueNode:
    def __init__(self, data):
        self.data = data
        self.next = None


class Queue:
    def __init__(self):
        self.front = None
        self.rear = None
        self.size = 0

    def is_empty(self):
        return self.front is None

    def enqueue(self, data):
        """Agrega al final. O(1)."""
        new_node = QueueNode(data)
        if self.rear is None:
            self.front = new_node
        else:
            self.rear.next = new_node
        self.rear = new_node
        self.size += 1

    def dequeue(self):
        """Saca y devuelve el del frente. O(1)."""
        if self.front is None:
            return None
        data = self.front.data
        self.front = self.front.next
        if self.front is None:
            self.rear = None
        self.size -= 1
        return data

    def peek(self):
        """Mira el del frente sin sacarlo. O(1)."""
        return None if self.front is None else self.front.data
