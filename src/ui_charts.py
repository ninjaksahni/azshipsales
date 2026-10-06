from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.fulfillment import Metric

_COLOR_TOP = "#16a34a"
_COLOR_SURGING = "#ca8a04"
_COLOR_DEFAULT = "#2563eb"


def bar_colors_for_priority_cities(cities: list[str], surging_cities: set[str]) -> list[str]:
    colors: list[str] = []
    for i, city in enumerate(cities):
        if i == 0:
            colors.append(_COLOR_TOP)
        elif city in surging_cities:
            colors.append(_COLOR_SURGING)
        else:
            colors.append(_COLOR_DEFAULT)
    return colors


def render_priority_markets_bar_chart(
    city_df: pd.DataFrame,
    metric: Metric,
    surging_cities: set[str],
) -> None:
    if city_df.empty:
        st.caption("No chart data.")
        return

    value_col = "Units" if metric == "units" else "Revenue (₹)"
    plot_df = city_df.sort_values(value_col, ascending=False).reset_index(drop=True)
    cities = plot_df["City"].astype(str).tolist()
    values = plot_df[value_col].tolist()
    colors = bar_colors_for_priority_cities(cities, surging_cities)

    fig = go.Figure(
        go.Bar(
            x=cities,
            y=values,
            marker_color=colors,
            hovertemplate="<b>%{x}</b><br>%{y}<extra></extra>",
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=8, r=8, t=12, b=80),
        xaxis_title="City",
        yaxis_title=value_col,
        xaxis=dict(tickangle=-35, categoryorder="array", categoryarray=cities),
        yaxis=dict(rangemode="tozero"),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
