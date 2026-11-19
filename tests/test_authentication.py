"""Authentication tests: encrypted passwords and session tokens."""
import os
import time
import unittest
from unittest import mock

import config
from authentication import tokens
from authentication.utilities import (
    HASH_ALGORITHM, browser_password_hash, encrypt_password, is_browser_password_hash, verify_password,
)


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


class BrowserPasswordHashTest(unittest.TestCase):
    # The same value src/passwordHash.ts computes in the browser (checked there with this email and password)
    PROFESSOR_HASH = "a510c5913ca39ffca313185cfdd70b28eab6333ecba817195e35e2cccef2bd76"

    def test_matches_the_browser_and_ignores_email_case_and_spaces(self):
        self.assertEqual(browser_password_hash("profe@prueba.co", "Clave2026"), self.PROFESSOR_HASH)
        self.assertEqual(browser_password_hash(" Profe@Prueba.co ", "Clave2026"), self.PROFESSOR_HASH)

    def test_password_is_not_readable_and_depends_on_the_email(self):
        sent = browser_password_hash("ana@correo.co", "Clave2026")
        self.assertNotIn("Clave2026", sent)
        self.assertNotEqual(sent, browser_password_hash("luis@correo.co", "Clave2026"))

    def test_only_a_sha256_value_is_accepted(self):
        self.assertTrue(is_browser_password_hash(self.PROFESSOR_HASH))
        for text in ("Clave2026", self.PROFESSOR_HASH.upper(), self.PROFESSOR_HASH[:-1], ""):
            self.assertFalse(is_browser_password_hash(text), text)

    def test_stored_hash_checks_the_value_the_browser_sends(self):
        stored = encrypt_password(self.PROFESSOR_HASH)
        self.assertTrue(verify_password(browser_password_hash("profe@prueba.co", "Clave2026"), stored))
        self.assertFalse(verify_password("Clave2026", stored))


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
