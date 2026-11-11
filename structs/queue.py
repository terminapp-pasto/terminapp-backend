"""Queue (FIFO) built from linked nodes.

First in, first out. In TerminAPP it holds pending reservations in arrival
order: the oldest one is at the front, so looking at the front is enough to
know whether any reservation has expired.
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
        """Adds at the end. O(1)."""
        new_node = QueueNode(data)
        if self.rear is None:
            self.front = new_node
        else:
            self.rear.next = new_node
        self.rear = new_node
        self.size += 1

    def dequeue(self):
        """Removes and returns the front item. O(1)."""
        if self.front is None:
            return None
        data = self.front.data
        self.front = self.front.next
        if self.front is None:
            self.rear = None
        self.size -= 1
        return data

    def peek(self):
        """Looks at the front item without removing it. O(1)."""
        return None if self.front is None else self.front.data
