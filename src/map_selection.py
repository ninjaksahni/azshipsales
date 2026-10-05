from __future__ import annotations

from typing import Any

import pandas as pd


def selected_cities_from_plotly_state(
    map_df: pd.DataFrame,
    selection: dict[str, Any] | None,
) -> pd.DataFrame:
    if not selection or map_df.empty:
        return map_df.iloc[0:0]

    indices = selection.get("point_indices") or []
    if not indices:
        points = selection.get("points") or []
        indices = [p.get("point_index") for p in points if p.get("point_index") is not None]

    if not indices:
        return map_df.iloc[0:0]

    valid = [i for i in indices if 0 <= i < len(map_df)]
    if not valid:
        return map_df.iloc[0:0]

    return map_df.iloc[valid].copy()


def summarize_area_selection(
    selected: pd.DataFrame,
    sku: str,
    sku_total_units: int,
) -> dict[str, Any]:
    if selected.empty:
        return {
            "sku": sku,
            "city_count": 0,
            "cities": [],
            "total_units": 0,
            "share_pct": 0.0,
        }

    total_units = int(selected["units"].sum())
    share = (total_units / sku_total_units * 100.0) if sku_total_units > 0 else 0.0
    cities = sorted(selected["City"].unique().tolist())

    return {
        "sku": sku,
        "city_count": len(cities),
        "cities": cities,
        "total_units": total_units,
        "share_pct": round(share, 1),
    }
