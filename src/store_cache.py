from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.store import DEFAULT_DATA_PATH, load_store


def store_mtime_ns(path: Path = DEFAULT_DATA_PATH) -> int:
    if not path.exists():
        return 0
    return path.stat().st_mtime_ns


def load_store_snapshot(path: Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    """Load store; use with Streamlit cache keyed on mtime."""
    return load_store(path)


def store_to_json_bytes(store: dict[str, Any]) -> bytes:
    return json.dumps(store, indent=2, ensure_ascii=False).encode("utf-8")
