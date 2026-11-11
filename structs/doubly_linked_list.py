"""Doubly linked list.

Each node knows the previous and the next one, so it can be walked both ways.
In TerminAPP it holds the user's purchase history: head to tail gives the
newest first, tail to head the oldest first, without sorting again.
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
        """Adds at the end. O(1)."""
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
        """Adds at the beginning. O(1)."""
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
        """Removes a node we already hold. O(1)."""
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
        """From head to tail. O(n)."""
        node = self.head
        while node is not None:
            visit(node.data)
            node = node.next

    def traverse_backward(self, visit):
        """From tail to head. O(n)."""
        node = self.tail
        while node is not None:
            visit(node.data)
            node = node.previous
