from __future__ import annotations

import unittest

from src.app_auth import passwords_match


class AppAuthTests(unittest.TestCase):
    def test_passwords_match(self) -> None:
        self.assertTrue(passwords_match(" secret ", "secret"))
        self.assertFalse(passwords_match("wrong", "secret"))


if __name__ == "__main__":
    unittest.main()
