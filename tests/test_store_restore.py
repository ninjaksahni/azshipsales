from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.store import load_store, new_store, restore_store_from_bytes, save_store


class StoreRestoreTests(unittest.TestCase):
    def test_restore_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregates.json"
            store = new_store()
            store["skus"]["SKU1"] = {"total_quantity": 3, "cities": {}}
            store["processed_keys"] = ["a"]
            save_store(store, path)

            payload = path.read_bytes()
            path.unlink()
            restored = restore_store_from_bytes(payload, path)
            self.assertEqual(restored["skus"]["SKU1"]["total_quantity"], 3)
            self.assertEqual(load_store(path)["processed_keys"], ["a"])

    def test_restore_rejects_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregates.json"
            with self.assertRaises(ValueError):
                restore_store_from_bytes(b"[]", path)
            with self.assertRaises(ValueError):
                restore_store_from_bytes(json.dumps({"foo": 1}).encode(), path)


if __name__ == "__main__":
    unittest.main()
