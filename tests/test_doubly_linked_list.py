"""Tests for the doubly linked list (structs/doubly_linked_list.py)."""
import unittest

from services.purchases import OLDEST_FIRST, purchase_history
from structs.doubly_linked_list import DoublyLinkedList


def forward(linked_list):
    items = []
    linked_list.traverse_forward(items.append)
    return items


def backward(linked_list):
    items = []
    linked_list.traverse_backward(items.append)
    return items


class DoublyLinkedListTest(unittest.TestCase):
    def test_traverse_both_ways(self):
        linked_list = DoublyLinkedList()
        for item in (2, 3):
            linked_list.append(item)
        linked_list.prepend(1)
        self.assertEqual(forward(linked_list), [1, 2, 3])
        self.assertEqual(backward(linked_list), [3, 2, 1])

    def test_remove_in_the_middle_and_at_the_ends(self):
        linked_list = DoublyLinkedList()
        nodes = [linked_list.append(n) for n in range(5)]
        linked_list.remove_node(nodes[2])
        linked_list.remove_node(nodes[0])
        linked_list.remove_node(nodes[4])
        self.assertEqual(forward(linked_list), [1, 3])
        self.assertEqual(backward(linked_list), [3, 1])
        self.assertEqual(linked_list.size, 2)

    def test_purchase_history(self):
        purchases = [{"id": 3}, {"id": 2}, {"id": 1}]  # they come from newest to oldest
        self.assertEqual([p["id"] for p in purchase_history(iter(purchases))], [3, 2, 1])
        self.assertEqual([p["id"] for p in purchase_history(iter(purchases), OLDEST_FIRST)], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
