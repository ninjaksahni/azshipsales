from __future__ import annotations

import unittest

from src.store_sync import _merge_geocode_dicts


class GeocodeSyncTests(unittest.TestCase):
    def test_merge_prefers_local_on_conflict(self) -> None:
        remote = {"A": {"lat": 1.0, "lon": 2.0}}
        local = {"A": {"failed": True}, "B": {"lat": 3.0, "lon": 4.0}}
        merged = _merge_geocode_dicts(remote, local)
        self.assertEqual(merged["A"], {"failed": True})
        self.assertEqual(merged["B"]["lat"], 3.0)


if __name__ == "__main__":
    unittest.main()
