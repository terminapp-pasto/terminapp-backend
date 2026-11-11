"""Authentication tests: encrypted passwords and session tokens."""
import os
import time
import unittest
from unittest import mock

import config
from authentication import tokens
from authentication.utilities import HASH_ALGORITHM, encrypt_password, verify_password


class PasswordTest(unittest.TestCase):
    def test_password_is_never_stored_as_is(self):
        stored = encrypt_password("Secreta2026")
        self.assertNotIn("Secreta2026", stored)
        self.assertTrue(stored.startswith(HASH_ALGORITHM + "$"))

    def test_same_password_gets_a_different_salt(self):
        self.assertNotEqual(encrypt_password("Secreta2026"), encrypt_password("Secreta2026"))

    def test_verify_password(self):
        stored = encrypt_password("Secreta2026")
        self.assertTrue(verify_password("Secreta2026", stored))
        self.assertFalse(verify_password("secreta2026", stored))

    def test_damaged_hash_is_rejected_without_crashing(self):
        for stored in ("", "texto", "md5$1$a$b", None):
            self.assertFalse(verify_password("Secreta2026", stored))


@mock.patch.object(config, "TOKEN_SECRET", "secreto-de-prueba")
class TokenTest(unittest.TestCase):
    def test_create_and_decode(self):
        claims = tokens.decode_token(tokens.create_token(7, "Ana"))
        self.assertEqual(claims["sub"], "7")
        self.assertEqual(claims["name"], "Ana")

    def test_tampered_token_is_rejected(self):
        header, payload, signature = tokens.create_token(7, "Ana").split(".")
        other_payload = tokens.create_token(1, "Admin").split(".")[1]
        with self.assertRaises(tokens.TokenError):
            tokens.decode_token(f"{header}.{other_payload}.{signature}")

    def test_malformed_token_is_rejected(self):
        for token in ("", "abc", "a.b", "a.b.c.d"):
            with self.assertRaises(tokens.TokenError):
                tokens.decode_token(token)

    def test_expired_token_is_rejected(self):
        token = tokens.create_token(7, "Ana")
        with mock.patch.object(time, "time", return_value=time.time() + tokens.TOKEN_LIFETIME_SECONDS + 1):
            with self.assertRaises(tokens.TokenError):
                tokens.decode_token(token)


if __name__ == "__main__":
    unittest.main()
