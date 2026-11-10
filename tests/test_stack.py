"""Pruebas de la pila (structs/stack.py)."""
import unittest

from services.purchases import FREE, RESERVED, build_seat_map, hold_seats
from structs.stack import Stack


class StackTest(unittest.TestCase):
    def test_last_in_first_out(self):
        stack = Stack()
        for seat in (5, 6, 7):
            stack.push(seat)
        self.assertEqual(stack.peek(), 7)
        self.assertEqual([stack.pop() for _ in range(3)], [7, 6, 5])
        self.assertTrue(stack.is_empty())
        self.assertIsNone(stack.pop())

    def test_undoes_a_half_done_reservation(self):
        seat_map = build_seat_map(40, [12])
        self.assertEqual(hold_seats(seat_map, [10, 11, 12, 13]), 12)
        for number in (10, 11, 13):
            self.assertEqual(seat_map.get(number), FREE)  # la pila los liberó

    def test_complete_reservation(self):
        seat_map = build_seat_map(40, [])
        self.assertIsNone(hold_seats(seat_map, [1, 2]))
        self.assertEqual(seat_map.get(1), RESERVED)


if __name__ == "__main__":
    unittest.main()
