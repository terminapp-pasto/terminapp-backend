"""The startup database scripts: they are split correctly and can run twice.

The database test needs PostgreSQL:
    TEST_DATABASE_URL=postgresql://... python -m unittest tests.test_migrations
"""

import os
import unittest
from unittest import mock

from services import migrations
from services.migrations import AUTOMATIC_SCRIPTS, SCRIPTS_FOLDER, split_statements

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


class SplitStatementsTest(unittest.TestCase):
    def test_comments_are_removed_and_statements_split(self):
        script = "-- adds a column; and explains it\nALTER TABLE a ADD b INT;\n\nUPDATE a SET b = 1;\n"
        self.assertEqual(split_statements(script), ["ALTER TABLE a ADD b INT", "UPDATE a SET b = 1"])

    def test_every_automatic_script_exists_and_has_statements(self):
        for name in AUTOMATIC_SCRIPTS:
            self.assertTrue(split_statements((SCRIPTS_FOLDER / name).read_text(encoding="utf-8")), name)


@unittest.skipUnless(TEST_DATABASE_URL, "needs TEST_DATABASE_URL")
class ApplyMigrationsTest(unittest.TestCase):
    def test_each_script_runs_only_once(self):
        with mock.patch("config.DATABASE_URL", TEST_DATABASE_URL):
            from services.database import connect

            with connect() as connection, connection.cursor() as cursor:
                cursor.execute("DROP TABLE IF EXISTS applied_migrations;")
            first = migrations.apply_pending_migrations()
            second = migrations.apply_pending_migrations()
        self.assertEqual(first, list(AUTOMATIC_SCRIPTS))
        self.assertEqual(second, [])


if __name__ == "__main__":
    unittest.main()
