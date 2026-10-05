from __future__ import annotations

import unittest
from datetime import date

from src.coverage import _heat_color


class CoverageTests(unittest.TestCase):
    def test_heat_color_darkens_with_count(self) -> None:
        self.assertEqual(_heat_color(0, 10), "#FFFFFF")
        self.assertEqual(_heat_color(10, 10), "rgb(127,17,17)")
        self.assertNotEqual(_heat_color(1, 10), _heat_color(9, 10))


if __name__ == "__main__":
    unittest.main()
