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


def sku_glance_dataframe(skus: dict[str, Any], metric: Metric) -> pd.DataFrame:
    rows = []
    value_label = "Units" if metric == "units" else "Revenue (₹)"
    for sku, data in skus.items():
        ranked = ranked_places_for_sku(data, "cities", metric, limit=3)
        if not ranked:
            continue
        top = ranked[0]
        row = {
            "SKU": sku,
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
    sort_col = value_label
    totals = {sku: _sku_total(skus[sku], metric) for sku in df["SKU"]}
    df["_sort"] = df["SKU"].map(totals)
    return df.sort_values("_sort", ascending=False).drop(columns="_sort").reset_index(drop=True)


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
