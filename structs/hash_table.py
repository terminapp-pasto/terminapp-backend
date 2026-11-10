"""Tabla hash con encadenamiento.

La tabla es un arreglo de tamaño fijo de "cubetas" (buckets). Cada clave pasa
por una función hash propia que dice en qué cubeta va, así se encuentra en O(1)
en promedio sin recorrer todo. Si dos claves caen en la misma cubeta (colisión),
se encadenan en una lista enlazada de nodos propios. Cuando la tabla se llena
más del 75 %, se duplica el tamaño y se reubican las claves (rehash).
"""

MAX_LOAD_FACTOR = 0.75
HASH_MULTIPLIER = 31
HASH_MODULUS = 1_000_000_007


class HashNode:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.next = None


class HashTable:
    def __init__(self, capacity=16):
        self.capacity = capacity
        # El arreglo de cubetas es solo memoria de tamaño fijo, como en C:
        # nunca crece con append; todos los datos viven en nodos HashNode.
        self.buckets = [None] * capacity
        self.size = 0

    def _bucket_index(self, key):
        """Hash polinómico propio sobre los caracteres de la clave (no usa hash() de Python)."""
        hash_value = 0
        for character in str(key):
            hash_value = (hash_value * HASH_MULTIPLIER + ord(character)) % HASH_MODULUS
        return hash_value % self.capacity

    def put(self, key, value):
        """Agrega la clave o actualiza su valor si ya existe. O(1) promedio."""
        index = self._bucket_index(key)
        node = self.buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        new_node = HashNode(key, value)
        new_node.next = self.buckets[index]
        self.buckets[index] = new_node
        self.size += 1

        if self.size / self.capacity > MAX_LOAD_FACTOR:
            self._resize()

    def get(self, key, default=None):
        """Devuelve el valor de la clave. O(1) promedio."""
        node = self.buckets[self._bucket_index(key)]
        while node is not None:
            if node.key == key:
                return node.value
            node = node.next
        return default

    def contains(self, key):
        node = self.buckets[self._bucket_index(key)]
        while node is not None:
            if node.key == key:
                return True
            node = node.next
        return False

    def remove(self, key):
        """Quita la clave. Devuelve True si estaba. O(1) promedio."""
        index = self._bucket_index(key)
        previous = None
        node = self.buckets[index]
        while node is not None:
            if node.key == key:
                if previous is None:
                    self.buckets[index] = node.next
                else:
                    previous.next = node.next
                self.size -= 1
                return True
            previous = node
            node = node.next
        return False

    def for_each(self, visit):
        """Llama visit(clave, valor) por cada elemento. O(n + capacidad)."""
        for index in range(self.capacity):
            node = self.buckets[index]
            while node is not None:
                visit(node.key, node.value)
                node = node.next

    def _resize(self):
        """Duplica la capacidad y vuelve a ubicar cada nodo en su nueva cubeta."""
        old_buckets = self.buckets
        old_capacity = self.capacity
        self.capacity *= 2
        self.buckets = [None] * self.capacity
        for index in range(old_capacity):
            node = old_buckets[index]
            while node is not None:
                next_node = node.next
                new_index = self._bucket_index(node.key)
                node.next = self.buckets[new_index]
                self.buckets[new_index] = node
                node = next_node
