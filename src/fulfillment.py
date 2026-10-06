from __future__ import annotations

from typing import Any, Literal

import pandas as pd

Metric = Literal["units", "revenue"]


def _metric_value(bucket: dict[str, Any], metric: Metric) -> float:
    if metric == "units":
        return float(int(bucket.get("quantity", 0)))
    return float(bucket.get("revenue_inr", 0.0))


def _sku_total(sku_data: dict[str, Any], metric: Metric) -> float:
    if metric == "units":
        return float(int(sku_data.get("total_quantity", 0)))
    return float(sku_data.get("total_revenue_inr", 0.0))


def _merge_place_bucket(into: dict[str, Any], bucket: dict[str, Any]) -> None:
    into["quantity"] = int(into.get("quantity", 0)) + int(bucket.get("quantity", 0))
    into["revenue_inr"] = float(into.get("revenue_inr", 0.0)) + float(
        bucket.get("revenue_inr", 0.0)
    )
    if bucket.get("state") and not into.get("state"):
        into["state"] = bucket["state"]
    by_day = bucket.get("by_day")
    if isinstance(by_day, dict):
        merged_days: dict[str, int] = into.setdefault("by_day", {})
        for day, qty in by_day.items():
            merged_days[day] = int(merged_days.get(day, 0)) + int(qty)


def merge_sku_records(skus: dict[str, Any], sku_names: list[str]) -> dict[str, Any]:
    """Combine city/state rollups (and per-city timelines) for multiple SKUs."""
    merged: dict[str, Any] = {
        "total_quantity": 0,
        "total_revenue_inr": 0.0,
        "cities": {},
        "states": {},
    }
    for name in sku_names:
        data = skus.get(name)
        if not data:
            continue
        merged["total_quantity"] += int(data.get("total_quantity", 0))
        merged["total_revenue_inr"] += float(data.get("total_revenue_inr", 0.0))
        for city, bucket in data.get("cities", {}).items():
            if city not in merged["cities"]:
                merged["cities"][city] = {
                    "quantity": 0,
                    "revenue_inr": 0.0,
                }
            _merge_place_bucket(merged["cities"][city], bucket)
        for state, bucket in data.get("states", {}).items():
            if state not in merged["states"]:
                merged["states"][state] = {
                    "quantity": 0,
                    "revenue_inr": 0.0,
                }
            _merge_place_bucket(merged["states"][state], bucket)
    return merged


def format_sku_selection_label(sku_names: list[str]) -> str:
    if not sku_names:
        return "—"
    if len(sku_names) == 1:
        return sku_names[0]
    if len(sku_names) == 2:
        return f"{sku_names[0]} + {sku_names[1]}"
    return f"{len(sku_names)} SKUs"


def ranked_places_for_sku(
    sku_data: dict[str, Any],
    bucket_key: str,
    metric: Metric,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    buckets = sku_data.get(bucket_key, {})
    total = _sku_total(sku_data, metric)
    rows: list[dict[str, Any]] = []
    for name, bucket in buckets.items():
        value = _metric_value(bucket, metric)
        if value <= 0:
            continue
        share = (value / total * 100.0) if total > 0 else 0.0
        rows.append(
            {
                "name": name,
                "value": value,
                "share_pct": round(share, 1),
            }
        )
    rows.sort(key=lambda r: r["value"], reverse=True)
    if limit is not None:
        return rows[:limit]
    return rows


def build_city_index(skus: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """City -> total units/revenue and per-SKU buckets."""
    index: dict[str, dict[str, Any]] = {}
    for sku, data in skus.items():
        for city, bucket in data.get("cities", {}).items():
            if city not in index:
                index[city] = {
                    "quantity": 0,
                    "revenue_inr": 0.0,
                    "skus": {},
                }
            entry = index[city]
            entry["quantity"] += int(bucket.get("quantity", 0))
            entry["revenue_inr"] += float(bucket.get("revenue_inr", 0.0))
            entry["skus"][sku] = bucket
    return index


def ranked_skus_for_city(
    city_index: dict[str, dict[str, Any]],
    city: str,
    metric: Metric,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    entry = city_index.get(city)
    if not entry:
        return []
    if metric == "units":
        total = float(entry["quantity"])
    else:
        total = float(entry["revenue_inr"])

    rows: list[dict[str, Any]] = []
    for sku, bucket in entry.get("skus", {}).items():
        value = _metric_value(bucket, metric)
        if value <= 0:
            continue
        share = (value / total * 100.0) if total > 0 else 0.0
        rows.append({"name": sku, "value": value, "share_pct": round(share, 1)})
    rows.sort(key=lambda r: r["value"], reverse=True)
    if limit is not None:
        return rows[:limit]
    return rows


def store_summary(skus: dict[str, Any]) -> dict[str, int | float]:
    city_index = build_city_index(skus)
    return {
        "sku_count": len(skus),
        "city_count": len(city_index),
        "total_units": sum(int(s.get("total_quantity", 0)) for s in skus.values()),
        "total_revenue_inr": sum(float(s.get("total_revenue_inr", 0)) for s in skus.values()),
    }


def skus_sorted(skus: dict[str, Any], metric: Metric) -> list[str]:
    return sorted(skus.keys(), key=lambda s: -_sku_total(skus[s], metric))


def cities_sorted(city_index: dict[str, dict[str, Any]], metric: Metric) -> list[str]:
    def total(c: str) -> float:
        e = city_index[c]
        return float(e["quantity"]) if metric == "units" else float(e["revenue_inr"])

    return sorted(city_index.keys(), key=lambda c: -total(c))


def filter_cities(cities: list[str], query: str) -> list[str]:
    q = query.strip().upper()
    if not q:
        return cities
    return [c for c in cities if q in c]


def sku_glance_dataframe(skus: dict[str, Any], metric: Metric) -> pd.DataFrame:
    rows = []
    value_label = "Top market (units)" if metric == "units" else "Top market (₹)"
    for sku, data in skus.items():
        ranked = ranked_places_for_sku(data, "cities", metric, limit=3)
        if not ranked:
            continue
        top = ranked[0]
        row = {
            "SKU": sku,
            "Total units": int(data.get("total_quantity", 0)),
            "Send most to": top["name"],
            value_label: int(top["value"]) if metric == "units" else round(top["value"], 2),
            "Share of SKU": f"{top['share_pct']}%",
        }
        if len(ranked) > 1:
            row["2nd market"] = ranked[1]["name"]
            row["3rd market"] = ranked[2]["name"] if len(ranked) > 2 else "—"
        else:
            row["2nd market"] = "—"
            row["3rd market"] = "—"
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    totals = {sku: _sku_total(skus[sku], metric) for sku in df["SKU"]}
    df["_sort"] = df["SKU"].map(totals)
    return df.sort_values("_sort", ascending=False).drop(columns="_sort").reset_index(drop=True)


def chart_series_from_table(df: pd.DataFrame, index_col: str, metric: Metric) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    value_col = "Units" if metric == "units" else "Revenue (₹)"
    return df.head(8).set_index(index_col)[value_col]


def places_table_df(ranked: list[dict[str, Any]], metric: Metric, place_label: str) -> pd.DataFrame:
    if not ranked:
        return pd.DataFrame()
    value_col = "Units" if metric == "units" else "Revenue (₹)"
    rows = []
    for i, r in enumerate(ranked, start=1):
        val = r["value"]
        if metric == "units":
            val = int(val)
        else:
            val = round(val, 2)
        rows.append(
            {
                "Priority": i,
                place_label: r["name"],
                value_col: val,
                "Share": f"{r['share_pct']}%",
            }
        )
    return pd.DataFrame(rows)


def format_hero_sku_to_city(sku: str, city: str, value: float, share: float, metric: Metric) -> str:
    if metric == "units":
        return (
            f"**Stock {sku} most in {city}** — "
            f"**{int(value)} units** ({share:.0f}% of this SKU's shipments)."
        )
    return (
        f"**Stock {sku} most in {city}** — "
        f"**₹{value:,.2f}** ({share:.0f}% of this SKU's revenue)."
    )


def format_hero_city_to_sku(city: str, sku: str, value: float, share: float, metric: Metric) -> str:
    if metric == "units":
        return (
            f"**In {city}, fulfill {sku} first** — "
            f"**{int(value)} units** ({share:.0f}% of that city's volume for your catalog)."
        )
    return (
        f"**In {city}, prioritize {sku}** — "
        f"**₹{value:,.2f}** ({share:.0f}% of that city's revenue)."
    )


def default_sku(skus: dict[str, Any], metric: Metric) -> str | None:
    if not skus:
        return None
    return max(skus.keys(), key=lambda s: _sku_total(skus[s], metric))


def default_city(city_index: dict[str, dict[str, Any]], metric: Metric) -> str | None:
    if not city_index:
        return None

    def city_total(c: str) -> float:
        e = city_index[c]
        return float(e["quantity"]) if metric == "units" else float(e["revenue_inr"])

    return max(city_index.keys(), key=city_total)
