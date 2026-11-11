"""Tests for the queue (structs/queue.py)."""
import unittest
from datetime import datetime, timedelta, timezone

from services.purchases import find_expired
from structs.queue import Queue


class QueueTest(unittest.TestCase):
    def test_first_in_first_out(self):
        queue = Queue()
        for ticket in (1, 2, 3):
            queue.enqueue(ticket)
        self.assertEqual(queue.peek(), 1)
        self.assertEqual([queue.dequeue() for _ in range(3)], [1, 2, 3])
        self.assertTrue(queue.is_empty())
        self.assertIsNone(queue.rear)

    def test_can_be_reused_after_emptied(self):
        queue = Queue()
        queue.enqueue("a")
        queue.dequeue()
        queue.enqueue("b")
        self.assertEqual(queue.dequeue(), "b")

    def test_expires_only_old_reservations(self):
        now = datetime.now(timezone.utc)
        minutes_ago = lambda minutes: now - timedelta(minutes=minutes)
        pending = [
            (1, "RESERVED", minutes_ago(50)),
            (2, "PAYING", minutes_ago(46)),    # more than 45: expires
            (3, "RESERVED", minutes_ago(20)),  # more than 15: expires
            (4, "PAYING", minutes_ago(30)),    # can still pay
            (5, "RESERVED", minutes_ago(5)),
        ]
        self.assertEqual(sorted(find_expired(pending, now)), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
