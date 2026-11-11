"""Stack (LIFO) built from linked nodes.

Last in, first out. In TerminAPP it works as an undo log: when several seats
are reserved each one is pushed; if one of them was already taken, they are
popped and released in reverse order, so no purchase is left half done.
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
        """Puts on top. O(1)."""
        new_node = StackNode(data)
        new_node.below = self.top
        self.top = new_node
        self.size += 1

    def pop(self):
        """Removes and returns the top item. O(1)."""
        if self.top is None:
            return None
        data = self.top.data
        self.top = self.top.below
        self.size -= 1
        return data

    def peek(self):
        return None if self.top is None else self.top.data
