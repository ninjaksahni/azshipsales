from __future__ import annotations

from typing import Any

from src.aggregate import _empty_bucket
from src.parser import ShipmentRow


def ensure_timeline_keys(store: dict[str, Any]) -> set[str]:
    keys = store.get("timeline_keys")
    if not isinstance(keys, list):
        keys = []
        store["timeline_keys"] = keys
    return set(keys)


def ensure_city_bucket_has_timeline(city_bucket: dict[str, Any]) -> dict[str, int]:
    by_day = city_bucket.get("by_day")
    if not isinstance(by_day, dict):
        by_day = {}
        city_bucket["by_day"] = by_day
    return by_day


def record_sku_city_timeline(
    store: dict[str, Any],
    row: ShipmentRow,
    city: str,
) -> bool:
    """Add one shipment to SKU+city daily timeline; idempotent per order+SKU."""
    if not row.shipment_date:
        return False
    timeline_keys = ensure_timeline_keys(store)
    if row.dedup_key in timeline_keys:
        return False

    skus = store.get("skus", {})
    sku_record = skus.get(row.merchant_sku)
    if not sku_record:
        return False

    cities = sku_record.get("cities", {})
    if city not in cities:
        return False

    by_day = ensure_city_bucket_has_timeline(cities[city])
    by_day[row.shipment_date] = int(by_day.get(row.shipment_date, 0)) + row.quantity

    timeline_keys.add(row.dedup_key)
    store["timeline_keys"] = sorted(timeline_keys)
    return True


def migrate_city_buckets(skus: dict[str, Any]) -> None:
    for data in skus.values():
        for city_bucket in data.get("cities", {}).values():
            ensure_city_bucket_has_timeline(city_bucket)
