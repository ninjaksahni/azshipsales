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
    total_units = int(sku_data.get("total_quantity", 0))

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
        units = int(bucket.get("quantity", 0))
        share_pct = (units / total_units * 100.0) if total_units > 0 else 0.0
        rows.append(
            {
                "City": display,
                "lat": lat,
                "lon": lon,
                "value": value,
                "metric_label": value_label,
                "share_pct": round(share_pct, 1),
            }
        )

    if not rows:
        return pd.DataFrame(), missing

    return pd.DataFrame(rows), missing


def _india_bubble_map(df: pd.DataFrame, sku: str, metric: Metric) -> Any:
    value_col = "value"
    plot_df = df.copy()

    plot_df["sku_label"] = sku
    plot_df["share_label"] = plot_df["share_pct"].apply(lambda p: f"{p:g}%")

    fig = px.scatter_map(
        plot_df,
        lat="lat",
        lon="lon",
        size=value_col,
        size_max=85,
        hover_name="City",
        custom_data=["sku_label", "share_label"],
        color=value_col,
        color_continuous_scale=["#FFE5E5", "#7F1111"],
        zoom=3.85,
        center={"lat": 22.8, "lon": 82.5},
        map_style="carto-positron",
        height=960,
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "SKU: %{customdata[0]}<br>"
            "%{customdata[1]} of this SKU's shipments"
            "<extra></extra>"
        ),
    )

    metric_word = "units shipped" if metric == "units" else "revenue (INR)"
    fig.update_layout(
        title=dict(text=f"{sku} — demand across India ({metric_word})", x=0.01, font_size=14),
        margin=dict(l=0, r=0, t=44, b=0, pad=0),
        coloraxis_showscale=False,
        autosize=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        map=dict(domain=dict(x=[0.0, 1.0], y=[0.0, 1.0])),
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

    st.markdown(
        """
        <style>
        div[data-testid="stPlotlyChart"] {
            width: 100% !important;
        }
        div[data-testid="stPlotlyChart"] > div {
            width: 100% !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        _india_bubble_map(df, sku_choice, metric),
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
    )

    if missing:
        with st.expander(f"Cities not on map ({len(missing)})"):
            st.caption("These cities are in your data but have no coordinates yet.")
            st.write(", ".join(sorted(missing)))
