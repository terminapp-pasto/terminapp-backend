"""Hash table with separate chaining.

The table is a fixed-size array of buckets. Each key goes through our own hash
function, which tells which bucket it belongs to, so lookups are O(1) on
average without scanning everything. When two keys land in the same bucket
(a collision) they are chained in a linked list of our own nodes. When the
table is more than 75% full it doubles its size and relocates the keys (rehash).
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
        # The bucket array is only fixed-size memory, like in C:
        # it never grows with append; all the data lives in HashNode nodes.
        self.buckets = [None] * capacity
        self.size = 0

    def _bucket_index(self, key):
        """Our own polynomial hash over the key's characters (does not use Python's hash())."""
        hash_value = 0
        for character in str(key):
            hash_value = (hash_value * HASH_MULTIPLIER + ord(character)) % HASH_MODULUS
        return hash_value % self.capacity

    def put(self, key, value):
        """Adds the key, or updates its value if it already exists. O(1) on average."""
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
        """Returns the key's value. O(1) on average."""
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
        """Removes the key. Returns True if it was there. O(1) on average."""
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
        """Calls visit(key, value) for every item. O(n + capacity)."""
        for index in range(self.capacity):
            node = self.buckets[index]
            while node is not None:
                visit(node.key, node.value)
                node = node.next

    def _resize(self):
        """Doubles the capacity and moves every node to its new bucket."""
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
