"""Security tests: broken tokens, the client address used for limits, the panel change
limit and the security headers sent with every answer."""
import unittest
from unittest import mock

from fastapi import HTTPException
from fastapi.testclient import TestClient

import config
from authentication import tokens
from routes import dependencies
from services.rate_limit import RateLimiter


def fake_request(headers=None, method="GET", host="10.0.0.1"):
    request = mock.Mock()
    request.headers = headers or {}
    request.method = method
    request.client = mock.Mock(host=host)
    return request


@mock.patch.object(config, "TOKEN_SECRET", "test-secret")
class BrokenTokenTest(unittest.TestCase):
    def test_strange_characters_are_rejected_not_a_crash(self):
        for token in ("a.b.ñ", "ñ.ñ.ñ", "a.b", "", "....", "a.b.c.d"):
            with self.assertRaises(tokens.TokenError):
                tokens.decode_token(token)

    def test_token_without_user_is_rejected(self):
        header = tokens._encode_base64url(b'{"alg":"HS256"}')
        payload = tokens._encode_base64url(b'{"exp": 9999999999}')
        content = f"{header}.{payload}"
        with self.assertRaises(tokens.TokenError):
            tokens.decode_token(f"{content}.{tokens._sign(content)}")

    def test_valid_token_still_works(self):
        claims = tokens.decode_token(tokens.create_token(7, "Ana"))
        self.assertEqual(claims["sub"], "7")


class ClientAddressTest(unittest.TestCase):
    def test_cloudflare_address_wins_over_a_faked_forwarded_for(self):
        request = fake_request({"cf-connecting-ip": "1.1.1.1", "x-forwarded-for": "6.6.6.6, 1.1.1.1"})
        self.assertEqual(dependencies.client_address(request), "1.1.1.1")

    def test_forwarded_for_is_the_fallback(self):
        self.assertEqual(dependencies.client_address(fake_request({"x-forwarded-for": "2.2.2.2, 3.3.3.3"})), "2.2.2.2")

    def test_direct_connection(self):
        self.assertEqual(dependencies.client_address(fake_request()), "10.0.0.1")

    def test_huge_header_is_cut(self):
        self.assertEqual(len(dependencies.client_address(fake_request({"cf-connecting-ip": "9" * 5000}))), 64)


class PanelChangeLimitTest(unittest.TestCase):
    def test_too_many_changes_are_stopped_but_reading_is_not(self):
        admin = {"id": 1, "role": "admin", "company_id": None}
        with mock.patch.object(dependencies, "ADMIN_WRITE_LIMITER", RateLimiter(3, 60)):
            for _ in range(3):
                dependencies.require_admin(fake_request(method="POST"), admin)
            with self.assertRaises(HTTPException) as caught:
                dependencies.require_staff(fake_request(method="POST"), admin)
            self.assertEqual(caught.exception.status_code, 429)
            self.assertEqual(dependencies.require_admin(fake_request(method="GET"), admin), admin)

    def test_each_account_has_its_own_count(self):
        with mock.patch.object(dependencies, "ADMIN_WRITE_LIMITER", RateLimiter(1, 60)):
            dependencies.require_admin(fake_request(method="POST"), {"id": 1, "role": "admin", "company_id": None})
            dependencies.require_staff(fake_request(method="POST"), {"id": 2, "role": "company", "company_id": 4})

    def test_traveller_never_gets_in(self):
        with self.assertRaises(HTTPException) as caught:
            dependencies.require_staff(fake_request(), {"id": 3, "role": "user", "company_id": None})
        self.assertEqual(caught.exception.status_code, 403)
        with self.assertRaises(HTTPException):
            dependencies.require_staff(fake_request(), {"id": 4, "role": "company", "company_id": None})


class SecurityHeadersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main
        cls.client = TestClient(main.app)  # no "with": the startup (database) does not run

    def test_headers_on_public_answers(self):
        response = self.client.get("/docs")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertIn("max-age", response.headers["strict-transport-security"])

    @mock.patch.object(config, "TOKEN_SECRET", "test-secret")
    def test_private_answers_are_not_cached(self):
        response = self.client.get("/me", headers=[(b"authorization", "Bearer a.b.ñ".encode())])
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["cache-control"], "no-store")


if __name__ == "__main__":
    unittest.main()
