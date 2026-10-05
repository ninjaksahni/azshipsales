from __future__ import annotations

from copy import deepcopy
from typing import Any


def _empty_bucket() -> dict[str, float | int]:
    return {"quantity": 0, "revenue_inr": 0.0}


def _add_to_bucket(bucket: dict[str, Any], quantity: int, revenue: float) -> None:
    bucket["quantity"] = int(bucket["quantity"]) + quantity
    bucket["revenue_inr"] = float(bucket["revenue_inr"]) + revenue


def _top_entry(buckets: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if not buckets:
        return None
    name, data = max(
        buckets.items(),
        key=lambda item: (int(item[1]["quantity"]), float(item[1]["revenue_inr"])),
    )
    return {
        "name": name,
        "quantity": int(data["quantity"]),
        "revenue_inr": round(float(data["revenue_inr"]), 2),
    }


def ensure_sku_record(store: dict[str, Any], sku: str) -> dict[str, Any]:
    skus = store.setdefault("skus", {})
    if sku not in skus:
        skus[sku] = {
            "total_quantity": 0,
            "total_revenue_inr": 0.0,
            "top_city": None,
            "top_state": None,
            "cities": {},
            "states": {},
        }
    return skus[sku]


def apply_shipment_to_sku(sku_record: dict[str, Any], city: str, state: str, quantity: int, revenue: float) -> None:
    sku_record["total_quantity"] = int(sku_record["total_quantity"]) + quantity
    sku_record["total_revenue_inr"] = round(
        float(sku_record["total_revenue_inr"]) + revenue, 2
    )

    cities = sku_record.setdefault("cities", {})
    if city not in cities:
        cities[city] = _empty_bucket()
    _add_to_bucket(cities[city], quantity, revenue)

    states = sku_record.setdefault("states", {})
    if state not in states:
        states[state] = _empty_bucket()
    _add_to_bucket(states[state], quantity, revenue)

    sku_record["top_city"] = _top_entry(cities)
    sku_record["top_state"] = _top_entry(states)


def recompute_sku_tops(sku_record: dict[str, Any]) -> None:
    sku_record["top_city"] = _top_entry(sku_record.get("cities", {}))
    sku_record["top_state"] = _top_entry(sku_record.get("states", {}))


def new_store() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "last_updated": None,
        "processed_keys": [],
        "uploads": [],
        "sales_by_day": {},
        "sales_day_keys": [],
        "skus": {},
    }


def clone_store(store: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(store)
