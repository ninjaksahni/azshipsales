from __future__ import annotations

import unittest

from src.ui_charts import bar_colors_for_priority_cities


class UiChartsTests(unittest.TestCase):
    def test_bar_colors(self) -> None:
        cities = ["MUMBAI", "PUNE", "DELHI"]
        colors = bar_colors_for_priority_cities(cities, {"PUNE"})
        self.assertEqual(colors[0], "#16a34a")
        self.assertEqual(colors[1], "#ca8a04")
        self.assertEqual(colors[2], "#2563eb")


if __name__ == "__main__":
    unittest.main()
