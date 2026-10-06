from __future__ import annotations

import unittest

from src.month_filter import apply_month_filter, day_in_months, month_keys_from_store


class MonthFilterTests(unittest.TestCase):
    def test_filter_one_month(self) -> None:
        store = {
            "sales_by_day": {"2025-09-01": 1, "2025-10-01": 1},
            "skus": {
                "A": {
                    "total_quantity": 5,
                    "total_revenue_inr": 500.0,
                    "cities": {
                        "MUMBAI": {
                            "quantity": 5,
                            "revenue_inr": 500.0,
                            "state": "MH",
                            "by_day": {"2025-09-01": 2, "2025-10-01": 3},
                        }
                    },
                    "states": {},
                }
            },
        }
        filtered = apply_month_filter(store, ["2025-09"])
        self.assertEqual(filtered["skus"]["A"]["total_quantity"], 2)
        self.assertEqual(filtered["skus"]["A"]["cities"]["MUMBAI"]["quantity"], 2)

    def test_month_keys(self) -> None:
        store = {"sales_by_day": {"2025-09-15": 1, "2025-10-02": 2}}
        self.assertEqual(month_keys_from_store(store), ["2025-09", "2025-10"])
        self.assertTrue(day_in_months("2025-09-15", {"2025-09"}))


if __name__ == "__main__":
    unittest.main()
