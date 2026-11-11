"""Tests for the schedule AVL tree (structs/avl_tree.py)."""
import unittest
from datetime import time

from structs.avl_tree import AVLTree, minutes_to_text, time_to_minutes


def real_height(node):
    if node is None:
        return 0
    return 1 + max(real_height(node.left), real_height(node.right))


def is_balanced(node):
    if node is None:
        return True
    difference = abs(real_height(node.left) - real_height(node.right))
    return difference <= 1 and is_balanced(node.left) and is_balanced(node.right)


class AVLTreeTest(unittest.TestCase):
    def test_time_conversion(self):
        self.assertEqual(time_to_minutes(time(21, 30)), 1290)
        self.assertEqual(minutes_to_text(1290), "21:30")
        self.assertEqual(minutes_to_text(5), "00:05")

    def test_stays_balanced_with_sorted_data(self):
        tree = AVLTree()
        for minutes in range(0, 1440, 15):  # the worst case for an unbalanced tree
            tree.insert(minutes, minutes, 1, 1000, 40)
        self.assertEqual(tree.size, 96)
        self.assertTrue(is_balanced(tree.root))
        self.assertLessEqual(tree.root.height, 9)  # log2(96) ≈ 6.6

    def test_traverse_from_a_time(self):
        tree = AVLTree()
        for minutes in (1260, 360, 750, 1080, 1320, 600):
            tree.insert(minutes, minutes, 1, 1000, 40)
        visited = []
        tree.traverse_from(1080, lambda node: visited.append(node.minutes))
        self.assertEqual(visited, [1080, 1260, 1320])  # only from 18:00 on, and in order

    def test_accepts_repeated_times(self):
        tree = AVLTree()
        tree.insert(600, 1, 1, 1000, 40)
        tree.insert(600, 2, 2, 2000, 40)
        visited = []
        tree.traverse_from(0, lambda node: visited.append(node.schedule_id))
        self.assertEqual(sorted(visited), [1, 2])


if __name__ == "__main__":
    unittest.main()
