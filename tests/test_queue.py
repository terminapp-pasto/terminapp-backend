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

    def test_expires_only_purchases_past_their_deadline(self):
        now = datetime.now(timezone.utc)
        minutes_from_now = lambda minutes: now + timedelta(minutes=minutes)
        pending = [  # sorted by deadline, earliest first
            (1, "RESERVED", minutes_from_now(-30)),
            (2, "PAYING", minutes_from_now(-1)),
            (3, "RESERVED", minutes_from_now(2)),   # still on time: the queue stops here
            (4, "PAYING", minutes_from_now(20)),
        ]
        self.assertEqual([ticket[0] for ticket in find_expired(pending, now)], [1, 2])

    def test_nothing_expires_when_everyone_is_on_time(self):
        now = datetime.now(timezone.utc)
        self.assertEqual(find_expired([(1, "PAYING", now + timedelta(minutes=5))], now), [])


if __name__ == "__main__":
    unittest.main()
