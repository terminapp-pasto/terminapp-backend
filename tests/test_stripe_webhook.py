"""Tests for the Stripe webhook signature check (payments/stripe_client.py)."""
import hashlib
import hmac
import json
import time
import unittest
from unittest import mock

import config
from payments.stripe_client import PaymentError, read_webhook_event

SECRET = "whsec_test_secret"


def sign(payload, timestamp=None, secret=SECRET):
    timestamp = str(int(time.time()) if timestamp is None else timestamp)
    signature = hmac.new(secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


@mock.patch.object(config, "STRIPE_WEBHOOK_SECRET", SECRET)
class StripeWebhookTest(unittest.TestCase):
    payload = json.dumps({"type": "checkout.session.completed", "data": {"object": {"id": "cs_1"}}}).encode()

    def test_accepts_a_real_stripe_signature(self):
        event = read_webhook_event(self.payload, sign(self.payload))
        self.assertEqual(event["type"], "checkout.session.completed")

    def test_rejects_a_fake_payment(self):
        with self.assertRaises(PaymentError):
            read_webhook_event(self.payload, sign(self.payload, secret="whsec_attacker"))

    def test_rejects_a_changed_payload(self):
        header = sign(self.payload)
        with self.assertRaises(PaymentError):
            read_webhook_event(self.payload.replace(b"cs_1", b"cs_2"), header)

    def test_rejects_old_or_missing_signatures(self):
        with self.assertRaises(PaymentError):
            read_webhook_event(self.payload, sign(self.payload, timestamp=time.time() - 3600))
        for header in (None, "", "t=123", "v1=abc"):
            with self.assertRaises(PaymentError):
                read_webhook_event(self.payload, header)


if __name__ == "__main__":
    unittest.main()
