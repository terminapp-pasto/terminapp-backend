"""Lista doblemente enlazada.

Cada nodo conoce al anterior y al siguiente, así se puede recorrer en los dos
sentidos. En TerminAPP guarda el historial de tiquetes del usuario: de la
cabeza hacia la cola son los más recientes primero, y al revés los más
antiguos primero, sin tener que volver a ordenar.
"""


class DoublyLinkedNode:
    def __init__(self, data):
        self.data = data
        self.previous = None
        self.next = None


class DoublyLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def is_empty(self):
        return self.head is None

    def append(self, data):
        """Agrega al final. O(1)."""
        new_node = DoublyLinkedNode(data)
        if self.tail is None:
            self.head = new_node
        else:
            new_node.previous = self.tail
            self.tail.next = new_node
        self.tail = new_node
        self.size += 1
        return new_node

    def prepend(self, data):
        """Agrega al inicio. O(1)."""
        new_node = DoublyLinkedNode(data)
        if self.head is None:
            self.tail = new_node
        else:
            new_node.next = self.head
            self.head.previous = new_node
        self.head = new_node
        self.size += 1
        return new_node

    def remove_node(self, node):
        """Quita un nodo que ya se tiene en la mano. O(1)."""
        if node.previous is None:
            self.head = node.next
        else:
            node.previous.next = node.next
        if node.next is None:
            self.tail = node.previous
        else:
            node.next.previous = node.previous
        node.previous = node.next = None
        self.size -= 1

    def traverse_forward(self, visit):
        """De la cabeza a la cola. O(n)."""
        node = self.head
        while node is not None:
            visit(node.data)
            node = node.next

    def traverse_backward(self, visit):
        """De la cola a la cabeza. O(n)."""
        node = self.tail
        while node is not None:
            visit(node.data)
            node = node.previous
