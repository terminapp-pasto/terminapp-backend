"""Pruebas del montículo de mínimos (structs/min_heap.py)."""
import random
import unittest

from structs.min_heap import MinHeap


class MinHeapTest(unittest.TestCase):
    def test_empty(self):
        heap = MinHeap()
        self.assertTrue(heap.is_empty())
        self.assertIsNone(heap.extract_min())

    def test_always_extracts_the_smallest(self):
        heap = MinHeap()
        for price in (72000, 61000, 90000, 72000, 16000):
            heap.insert(price, price)
        self.assertEqual([heap.extract_min() for _ in range(5)], [16000, 61000, 72000, 72000, 90000])
        self.assertTrue(heap.is_empty())

    def test_sorts_many_items(self):
        items = random.sample(range(100000), 500)
        heap = MinHeap()
        for item in items:
            heap.insert(item, item)
        self.assertEqual([heap.extract_min() for _ in items], sorted(items))

    def test_interleaved_insert_and_extract(self):
        heap = MinHeap()
        heap.insert(5, "cinco")
        heap.insert(3, "tres")
        self.assertEqual(heap.extract_min(), "tres")
        heap.insert(1, "uno")
        self.assertEqual(heap.extract_min(), "uno")
        self.assertEqual(heap.extract_min(), "cinco")


if __name__ == "__main__":
    unittest.main()
