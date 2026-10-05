from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.city_coords import city_coordinates, normalize_city_name
from src.constants import SESSION_MAP_SKU
from src.fulfillment import Metric
from src.sku_selection import ensure_default_sku, ensure_map_sku


def _sku_city_map_df(sku_data: dict[str, Any], metric: Metric) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []

    for city, bucket in sku_data.get("cities", {}).items():
        if metric == "units":
            value = int(bucket.get("quantity", 0))
            value_label = "Units"
        else:
            value = float(bucket.get("revenue_inr", 0.0))
            value_label = "Revenue (₹)"

        if value <= 0:
            continue

        coords = city_coordinates(city)
        if not coords:
            missing.append(city)
            continue

        lat, lon = coords
        display = normalize_city_name(city) if normalize_city_name(city) else city
        rows.append(
            {
                "City": display,
                "lat": lat,
                "lon": lon,
                "value": value,
                "metric_label": value_label,
            }
        )

    if not rows:
        return pd.DataFrame(), missing

    return pd.DataFrame(rows), missing


def _format_hover_value(metric: Metric, value: float) -> str:
    if metric == "units":
        return f"{int(value):,}"
    return f"₹{value:,.2f}"


def _india_bubble_map(df: pd.DataFrame, sku: str, metric: Metric) -> Any:
    value_col = "value"
    plot_df = df.copy()
    plot_df["hover_value"] = plot_df[value_col].apply(
        lambda v: _format_hover_value(metric, v)
    )

    fig = px.scatter_geo(
        plot_df,
        lat="lat",
        lon="lon",
        size=value_col,
        size_max=70,
        hover_name="City",
        custom_data=["metric_label", "hover_value"],
        scope="asia",
        color=value_col,
        color_continuous_scale=["#FFE5E5", "#7F1111"],
    )

    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]}: %{customdata[1]}<extra></extra>",
    )

    fig.update_geos(
        visible=True,
        resolution=50,
        showcountries=True,
        countrycolor="#9aa0a6",
        showland=True,
        landcolor="#f5f5f5",
        showocean=True,
        oceancolor="#e8f4fc",
        lataxis_range=[6.5, 37.5],
        lonaxis_range=[67.5, 97.5],
        center=dict(lat=22.8, lon=82.5),
        projection_scale=2.65,
    )

    metric_word = "units shipped" if metric == "units" else "revenue (INR)"
    fig.update_layout(
        title=dict(text=f"{sku} — demand across India ({metric_word})", x=0.01, font_size=14),
        margin=dict(l=0, r=0, t=44, b=0),
        coloraxis_showscale=False,
        height=720,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_maps_tab(skus: dict[str, Any], metric: Metric) -> None:
    st.markdown("##### Map — where this SKU ships")
    st.caption("Bubble size shows demand in each city. Larger bubble = more shipments for the selected SKU.")

    sku_list = ensure_default_sku(skus, metric)
    ensure_map_sku(skus, metric)

    sku_choice = st.pills(
        "Product (SKU)",
        options=sku_list,
        selection_mode="single",
        key=SESSION_MAP_SKU,
        label_visibility="collapsed",
    )
    if not sku_choice:
        sku_choice = st.session_state[SESSION_MAP_SKU]

    rec = skus[sku_choice]
    df, missing = _sku_city_map_df(rec, metric)

    if df.empty:
        st.warning("No mappable cities for this SKU yet.")
        return

    st.plotly_chart(_india_bubble_map(df, sku_choice, metric), use_container_width=True)

    if missing:
        with st.expander(f"Cities not on map ({len(missing)})"):
            st.caption("These cities are in your data but have no coordinates yet.")
            st.write(", ".join(sorted(missing)))
