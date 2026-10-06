from __future__ import annotations

import unittest

from src.app_auth import _auth_token, passwords_match


class AppAuthTests(unittest.TestCase):
    def test_passwords_match(self) -> None:
        self.assertTrue(passwords_match(" secret ", "secret"))
        self.assertFalse(passwords_match("wrong", "secret"))

    def test_auth_token_stable(self) -> None:
        self.assertEqual(_auth_token("abc"), _auth_token("abc"))
        self.assertNotEqual(_auth_token("abc"), _auth_token("abcd"))


if __name__ == "__main__":
    unittest.main()
