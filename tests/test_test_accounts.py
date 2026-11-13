"""The company manager test account is linked to its company.

Needs PostgreSQL:
    TEST_DATABASE_URL=postgresql://... python -m unittest tests.test_test_accounts
"""

import os
import unittest
from unittest import mock

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@unittest.skipUnless(TEST_DATABASE_URL, "needs TEST_DATABASE_URL")
class CompanyAccountTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch("config.DATABASE_URL", TEST_DATABASE_URL)
        patcher.start()
        self.addCleanup(patcher.stop)
        from services import users

        self.users = users
        users.upsert_user("Empresa de prueba", "empresa.profe@terminapp.co", "hash", users.ROLE_USER)

    def test_account_manages_the_company_named(self):
        self.assertTrue(self.users.make_company_account("empresa.profe@terminapp.co", "expreso bolivariano"))
        account = self.users.find_user_by_email("empresa.profe@terminapp.co")
        self.assertEqual(account["role"], self.users.ROLE_COMPANY)
        self.assertEqual(account["company"], "EXPRESO BOLIVARIANO")

    def test_unknown_company_leaves_the_account_as_it_was(self):
        self.assertFalse(self.users.make_company_account("empresa.profe@terminapp.co", "PEPITO PEREZ"))
        self.assertEqual(self.users.find_user_by_email("empresa.profe@terminapp.co")["role"], self.users.ROLE_USER)


if __name__ == "__main__":
    unittest.main()
