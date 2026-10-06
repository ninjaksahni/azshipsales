from __future__ import annotations

import unittest

from src.ui_charts import _bar_top_icons, bar_colors_for_priority_cities


class UiChartsTests(unittest.TestCase):
    def test_bar_colors(self) -> None:
        cities = ["MUMBAI", "PUNE", "DELHI"]
        colors = bar_colors_for_priority_cities(cities, {"PUNE"})
        self.assertEqual(colors[0], "#2563eb")
        self.assertEqual(colors[1], "#a3e635")
        self.assertEqual(colors[2], "#2563eb")

    def test_bar_top_icons(self) -> None:
        icons = _bar_top_icons(["MUMBAI", "PUNE", "DELHI"], [10, 8, 3], {"PUNE"})
        texts = [a["text"] for a in icons]
        self.assertEqual(texts, ["👑", "🚀"])


if __name__ == "__main__":
    unittest.main()
