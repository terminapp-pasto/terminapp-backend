"""Request limits per client, to stop password guessing, mass sign-ups and seat hoarding.

Sliding window built with our own structures: a HashTable maps each client (its IP
address) to a Queue with the times of its recent requests. On each request the old
times leave the front of the queue; if the queue is still full, the request is refused.
Each check costs O(1) on average plus the times that leave the window.
"""

import time

from structs.hash_table import HashTable
from structs.queue import Queue


class RateLimiter:
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests_by_client = HashTable()

    def allow(self, client_key, now=None):
        """True if the client may make another request now; the request is then counted."""
        now = time.monotonic() if now is None else now
        recent = self.requests_by_client.get(client_key)
        if recent is None:
            recent = Queue()
            self.requests_by_client.put(client_key, recent)
        while not recent.is_empty() and recent.peek() <= now - self.window_seconds:
            recent.dequeue()
        if recent.size >= self.max_requests:
            return False
        recent.enqueue(now)
        return True

    def seconds_until_allowed(self, client_key, now=None):
        """How long the client must wait before the next request is accepted."""
        now = time.monotonic() if now is None else now
        recent = self.requests_by_client.get(client_key)
        if recent is None or recent.size < self.max_requests:
            return 0
        return max(0, int(recent.peek() + self.window_seconds - now) + 1)


# One limiter per kind of action
LOGIN_LIMITER = RateLimiter(max_requests=5, window_seconds=60)
REGISTER_LIMITER = RateLimiter(max_requests=3, window_seconds=600)
CHAT_LIMITER = RateLimiter(max_requests=10, window_seconds=60)
PURCHASE_LIMITER = RateLimiter(max_requests=10, window_seconds=600)
PAYMENT_LIMITER = RateLimiter(max_requests=20, window_seconds=600)
ADMIN_WRITE_LIMITER = RateLimiter(max_requests=60, window_seconds=60)  # panel changes, per client
