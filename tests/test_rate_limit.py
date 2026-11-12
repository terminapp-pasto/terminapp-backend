"""Tests for the request limiter (services/rate_limit.py), built with HashTable + Queue."""
import unittest

from services.rate_limit import RateLimiter


class RateLimiterTest(unittest.TestCase):
    def test_blocks_after_the_limit(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        results = [limiter.allow("1.2.3.4", now=10 + i) for i in range(7)]
        self.assertEqual(results, [True, True, True, True, True, False, False])

    def test_each_client_has_its_own_count(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        self.assertTrue(limiter.allow("ana", now=0))
        self.assertTrue(limiter.allow("luis", now=0))
        self.assertFalse(limiter.allow("ana", now=1))

    def test_window_slides(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.allow("ip", now=0)
        limiter.allow("ip", now=30)
        self.assertFalse(limiter.allow("ip", now=59))
        self.assertTrue(limiter.allow("ip", now=61))   # the request at second 0 left the window
        self.assertEqual(limiter.seconds_until_allowed("ip", now=62), 29)

    def test_thirty_wrong_passwords_are_stopped(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        accepted = sum(limiter.allow("attacker", now=i * 0.1) for i in range(30))
        self.assertEqual(accepted, 5)


if __name__ == "__main__":
    unittest.main()
