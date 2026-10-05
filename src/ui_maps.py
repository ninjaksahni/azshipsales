from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.city_coords import city_coordinates, normalize_city_name
from src.constants import SESSION_MAP_SKU
from src.fulfillment import Metric
from src.map_selection import selected_cities_from_plotly_state, summarize_area_selection
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
                "units": units,
                "metric_label": value_label,
                "share_pct": round(share_pct, 1),
            }
        )

    if not rows:
        return pd.DataFrame(), missing

    return pd.DataFrame(rows).reset_index(drop=True), missing


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
        dragmode="pan",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        map=dict(domain=dict(x=[0.0, 1.0], y=[0.0, 1.0])),
    )
    return fig


def _render_selection_panel(summary: dict[str, Any]) -> None:
    st.markdown("##### Selected area of interest")
    if summary["city_count"] == 0:
        st.info(
            "**Pan:** drag the map to move. **Select area:** use the **box select** tool "
            "in the map toolbar (top-right), then drag a rectangle over cities."
        )
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Share of this SKU", f"{summary['share_pct']}%")
    c2.metric("Total shipments", f"{summary['total_units']:,}")
    c3.metric("Cities included", summary["city_count"])

    st.caption(f"SKU: **{summary['sku']}**")
    st.markdown("**Cities in selection**")
    st.write(", ".join(summary["cities"]))


def render_maps_tab(skus: dict[str, Any], metric: Metric) -> None:
    st.markdown("##### Map — where this SKU ships")
    st.caption(
        "Drag to **pan** the map. Use the toolbar **box select** tool, then drag a "
        "rectangle to summarize shipments in that area."
    )

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
    sku_total_units = int(rec.get("total_quantity", 0))

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

    chart_key = f"india_map_select_{sku_choice}"
    plotly_state = st.plotly_chart(
        _india_bubble_map(df, sku_choice, metric),
        use_container_width=True,
        on_select="rerun",
        selection_mode=("box", "points"),
        key=chart_key,
        config={
            "displayModeBar": True,
            "modeBarButtonsToRemove": [
                "zoom2d",
                "zoomIn2d",
                "zoomOut2d",
                "autoScale2d",
                "resetScale2d",
                "lasso2d",
            ],
            "responsive": True,
        },
    )

    selection_dict: dict[str, Any] | None = None
    if plotly_state is not None and hasattr(plotly_state, "selection"):
        selection_dict = plotly_state.selection
    elif plotly_state is not None and isinstance(plotly_state, dict):
        selection_dict = plotly_state.get("selection")

    selected_df = selected_cities_from_plotly_state(df, selection_dict)
    summary = summarize_area_selection(selected_df, sku_choice, sku_total_units)
    _render_selection_panel(summary)

    if missing:
        with st.expander(f"Cities not on map ({len(missing)})"):
            st.caption("These cities are in your data but have no coordinates yet.")
            st.write(", ".join(sorted(missing)))
