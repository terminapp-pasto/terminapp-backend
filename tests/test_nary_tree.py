"""Tests for the n-ary tree (structs/nary_tree.py)."""
import unittest

from structs.nary_tree import NaryTree


def child_names(node):
    names, child = [], node.first_child
    while child is not None:
        names.append(child.name)
        child = child.next_sibling
    return names


class NaryTreeTest(unittest.TestCase):
    def test_terminal_companies_routes_hierarchy(self):
        tree = NaryTree("Terminal de Pasto")
        bolivariano = tree.root.get_or_create_child("EXPRESO BOLIVARIANO")
        bolivariano.get_or_create_child("Pasto → Cali")
        bolivariano.get_or_create_child("Pasto → Ipiales")
        tree.root.get_or_create_child("TRANSIPIALES")
        self.assertEqual(child_names(tree.root), ["EXPRESO BOLIVARIANO", "TRANSIPIALES"])
        self.assertEqual(child_names(bolivariano), ["Pasto → Cali", "Pasto → Ipiales"])

    def test_get_or_create_does_not_duplicate(self):
        tree = NaryTree("Terminal")
        first = tree.root.get_or_create_child("TRANSANDONA")
        second = tree.root.get_or_create_child("TRANSANDONA")
        self.assertIs(first, second)
        self.assertEqual(len(child_names(tree.root)), 1)

    def test_find_missing_child(self):
        self.assertIsNone(NaryTree("Terminal").root.find_child("Nadie"))

    def test_describe_indents_by_level(self):
        tree = NaryTree("Terminal")
        tree.root.get_or_create_child("TRANSANDONA").get_or_create_child("Pasto → Sandoná")
        self.assertEqual(tree.describe(), "Terminal\n    TRANSANDONA\n        Pasto → Sandoná")


if __name__ == "__main__":
    unittest.main()
