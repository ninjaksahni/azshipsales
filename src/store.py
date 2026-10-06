from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.aggregate import apply_shipment_to_sku, ensure_sku_record, new_store
from src.coverage import ensure_sales_by_day, ensure_sales_day_keys, record_shipment_day_for_row
from src.parser import ShipmentRow
from src.timeline import migrate_city_buckets, record_sku_city_timeline

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "aggregates.json"


def load_store(path: Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    if not path.exists():
        return new_store()
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if "processed_keys" not in data:
        data["processed_keys"] = []
    if "skus" not in data:
        data["skus"] = {}
    if "uploads" not in data:
        data["uploads"] = []
    ensure_sales_by_day(data)
    ensure_sales_day_keys(data)
    if "timeline_keys" not in data:
        data["timeline_keys"] = []
    migrate_city_buckets(data.get("skus", {}))
    return data


def save_store(store: dict[str, Any], path: Path = DEFAULT_DATA_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    store["last_updated"] = datetime.now(timezone.utc).isoformat()
    with path.open("w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
        f.write("\n")

    from src.store_sync import push_store_snapshot

    push_store_snapshot(store, path)


def ingest_rows(
    store: dict[str, Any],
    rows: list[ShipmentRow],
    filename: str,
    rows_read: int,
    rows_skipped_zero_amount: int,
) -> dict[str, int]:
    processed = set(store.get("processed_keys", []))
    imported = 0
    skipped_duplicate = 0
    coverage_backfilled = 0
    timeline_backfilled = 0

    for row in rows:
        key = row.dedup_key
        city = row.city or "UNKNOWN"
        if key in processed:
            skipped_duplicate += 1
            if record_shipment_day_for_row(store, row):
                coverage_backfilled += 1
            if record_sku_city_timeline(store, row, city):
                timeline_backfilled += 1
            continue

        sku_record = ensure_sku_record(store, row.merchant_sku)
        apply_shipment_to_sku(
            sku_record,
            city,
            row.state or "UNKNOWN",
            row.quantity,
            row.product_amount,
        )
        record_shipment_day_for_row(store, row)
        record_sku_city_timeline(store, row, city)
        processed.add(key)
        imported += 1

    store["processed_keys"] = sorted(processed)
    store.setdefault("uploads", []).append(
        {
            "filename": filename,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "rows_read": rows_read,
            "rows_imported": imported,
            "rows_skipped_duplicate": skipped_duplicate,
            "rows_skipped_zero_amount": rows_skipped_zero_amount,
            "coverage_days_backfilled": coverage_backfilled,
            "timeline_backfilled": timeline_backfilled,
        }
    )

    return {
        "rows_imported": imported,
        "rows_skipped_duplicate": skipped_duplicate,
        "rows_skipped_zero_amount": rows_skipped_zero_amount,
        "coverage_days_backfilled": coverage_backfilled,
        "timeline_backfilled": timeline_backfilled,
    }


def reset_store(path: Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    store = new_store()
    save_store(store, path)
    return store


def restore_store_from_bytes(payload: bytes, path: Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("File is not valid UTF-8 JSON.") from exc
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object at the top level.")
    if "skus" not in data and "processed_keys" not in data:
        raise ValueError(
            "This does not look like an aggregates backup (missing skus or processed_keys)."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return load_store(path)
