from __future__ import annotations

import unittest
from datetime import date

from src.velocity import city_momentum, classify_momentum


class VelocityTests(unittest.TestCase):
    def test_classify_surging(self) -> None:
        label, headline, _, pct = classify_momentum(6, 2)
        self.assertEqual(label, "surging")
        self.assertIsNotNone(pct)

    def test_classify_new(self) -> None:
        label, _, _, _ = classify_momentum(3, 0)
        self.assertEqual(label, "new")

    def test_city_momentum_windows(self) -> None:
        end = date(2026, 10, 4)
        by_day = {}
        for i in range(7):
            d = end - __import__("datetime").timedelta(days=i)
            by_day[d.isoformat()] = 2
        prior_end = end - __import__("datetime").timedelta(days=7)
        for i in range(7):
            d = prior_end - __import__("datetime").timedelta(days=i)
            by_day[d.isoformat()] = 1
        m = city_momentum("MUMBAI", by_day, end)
        self.assertIsNotNone(m)
        assert m is not None
        self.assertEqual(m.recent_units, 14)
        self.assertEqual(m.prior_units, 7)
        self.assertIn(m.label, ("surging", "growing"))


if __name__ == "__main__":
    unittest.main()
