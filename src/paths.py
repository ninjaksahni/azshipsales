from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
AGGREGATES_PATH = ROOT_DIR / "data" / "aggregates.json"
GEOCODE_CACHE_PATH = ROOT_DIR / "data" / "geocode_cache.json"
