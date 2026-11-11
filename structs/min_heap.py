"""Min-heap built from linked nodes.

The root always holds the smallest key (for example the lowest price).
To reach position n in the tree we follow the bits of n in binary:
0 = left, 1 = right.
"""


class HeapNode:
    def __init__(self, key, data):
        self.key = key
        self.data = data
        self.left = None
        self.right = None
        self.parent = None


class MinHeap:
    def __init__(self):
        self.root = None
        self.size = 0

    def is_empty(self):
        return self.size == 0

    def _node_at(self, position):
        power = 1
        while power * 2 <= position:
            power *= 2
        node = self.root
        power //= 2
        while power >= 1:
            if (position // power) % 2 == 1:
                node = node.right
            else:
                node = node.left
            power //= 2
        return node

    def _swap(self, first, second):
        first.key, second.key = second.key, first.key
        first.data, second.data = second.data, first.data

    def _sift_up(self, node):
        while node.parent is not None and node.key < node.parent.key:
            self._swap(node, node.parent)
            node = node.parent

    def insert(self, key, data):
        new_node = HeapNode(key, data)
        self.size += 1
        if self.root is None:
            self.root = new_node
            return
        parent = self._node_at(self.size // 2)
        new_node.parent = parent
        if parent.left is None:
            parent.left = new_node
        else:
            parent.right = new_node
        self._sift_up(new_node)

    def _sift_down(self, node):
        while True:
            smallest = node
            if node.left is not None and node.left.key < smallest.key:
                smallest = node.left
            if node.right is not None and node.right.key < smallest.key:
                smallest = node.right
            if smallest is node:
                return
            self._swap(node, smallest)
            node = smallest

    def extract_min(self):
        if self.root is None:
            return None
        data = self.root.data
        last = self._node_at(self.size)
        if last is self.root:
            self.root = None
        else:
            self.root.key = last.key
            self.root.data = last.data
            parent = last.parent
            if parent.right is last:
                parent.right = None
            else:
                parent.left = None
            self._sift_down(self.root)
        self.size -= 1
        return data
