from __future__ import annotations

import unittest

from src.fulfillment import (
    build_city_index,
    filter_cities,
    ranked_places_for_sku,
    ranked_skus_for_city,
    skus_sorted,
)


class FulfillmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skus = {
            "A": {
                "total_quantity": 10,
                "total_revenue_inr": 1000.0,
                "cities": {
                    "MUMBAI": {"quantity": 6, "revenue_inr": 600.0},
                    "PUNE": {"quantity": 4, "revenue_inr": 400.0},
                },
                "states": {},
            },
            "B": {
                "total_quantity": 5,
                "total_revenue_inr": 500.0,
                "cities": {
                    "MUMBAI": {"quantity": 5, "revenue_inr": 500.0},
                },
                "states": {},
            },
        }

    def test_ranked_cities_share(self) -> None:
        ranked = ranked_places_for_sku(self.skus["A"], "cities", "units")
        self.assertEqual(ranked[0]["name"], "MUMBAI")
        self.assertEqual(ranked[0]["share_pct"], 60.0)

    def test_city_index_and_sku_rank(self) -> None:
        index = build_city_index(self.skus)
        self.assertEqual(index["MUMBAI"]["quantity"], 11)
        ranked = ranked_skus_for_city(index, "MUMBAI", "units")
        self.assertEqual(ranked[0]["name"], "A")

    def test_filter_cities(self) -> None:
        cities = ["MUMBAI", "BENGALURU", "PUNE"]
        self.assertEqual(filter_cities(cities, "mum"), ["MUMBAI"])

    def test_skus_sorted(self) -> None:
        self.assertEqual(skus_sorted(self.skus, "units")[0], "A")


if __name__ == "__main__":
    unittest.main()
