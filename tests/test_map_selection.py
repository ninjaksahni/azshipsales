from __future__ import annotations

import unittest

import pandas as pd

from src.map_selection import selected_cities_from_plotly_state, summarize_area_selection


class MapSelectionTests(unittest.TestCase):
    def test_selection_by_indices(self) -> None:
        df = pd.DataFrame(
            {
                "City": ["MUMBAI", "PUNE"],
                "units": [10, 5],
            }
        )
        sel = {"point_indices": [0]}
        out = selected_cities_from_plotly_state(df, sel)
        self.assertEqual(len(out), 1)
        self.assertEqual(out.iloc[0]["City"], "MUMBAI")

    def test_summarize(self) -> None:
        selected = pd.DataFrame({"City": ["MUMBAI", "PUNE"], "units": [10, 5]})
        s = summarize_area_selection(selected, "DG2", 30)
        self.assertEqual(s["total_units"], 15)
        self.assertEqual(s["share_pct"], 50.0)
        self.assertEqual(s["city_count"], 2)


if __name__ == "__main__":
    unittest.main()
