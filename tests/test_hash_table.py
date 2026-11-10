"""Pruebas de la tabla hash con encadenamiento (structs/hash_table.py)."""
import random
import unittest

from structs.hash_table import MAX_LOAD_FACTOR, HashTable


class HashTableTest(unittest.TestCase):
    def test_put_get_and_update(self):
        table = HashTable()
        table.put(12, "FREE")
        table.put(12, "TAKEN")
        self.assertEqual(table.get(12), "TAKEN")
        self.assertEqual(table.size, 1)
        self.assertEqual(table.get(99, "NO"), "NO")

    def test_collisions(self):
        table = HashTable(2)  # pocas cubetas a propósito
        for key in ("abc", "cab", "bca"):  # mismas letras, distintas claves
            table.put(key, key.upper())
        for key in ("abc", "cab", "bca"):
            self.assertEqual(table.get(key), key.upper())

    def test_remove(self):
        table = HashTable()
        table.put("a", 1)
        self.assertTrue(table.remove("a"))
        self.assertFalse(table.remove("a"))
        self.assertFalse(table.contains("a"))
        self.assertEqual(table.size, 0)

    def test_grows_without_losing_data(self):
        table = HashTable(4)
        keys = random.sample(range(10**6), 2000)
        for key in keys:
            table.put(key, key * 2)
        self.assertGreater(table.capacity, 2000 / MAX_LOAD_FACTOR)
        self.assertTrue(all(table.get(k) == k * 2 for k in keys))

    def test_for_each(self):
        table = HashTable()
        for number in range(1, 41):
            table.put(number, "FREE")
        visited = []
        table.for_each(lambda key, value: visited.append(key))
        self.assertEqual(sorted(visited), list(range(1, 41)))


if __name__ == "__main__":
    unittest.main()
