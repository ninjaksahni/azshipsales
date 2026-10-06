from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.fulfillment import Metric

_COLOR_SURGING = "#a3e635"
_COLOR_DEFAULT = "#2563eb"


def bar_colors_for_priority_cities(cities: list[str], surging_cities: set[str]) -> list[str]:
    colors: list[str] = []
    for i, city in enumerate(cities):
        if i != 0 and city in surging_cities:
            colors.append(_COLOR_SURGING)
        else:
            colors.append(_COLOR_DEFAULT)
    return colors


def _bar_top_icons(
    cities: list[str],
    values: list[float],
    surging_cities: set[str],
) -> list[dict]:
    annotations: list[dict] = []
    for i, (city, value) in enumerate(zip(cities, values)):
        if value <= 0:
            continue
        if i == 0:
            icon = "👑"
        elif city in surging_cities:
            icon = "🚀"
        else:
            continue
        annotations.append(
            {
                "x": city,
                "y": value,
                "text": icon,
                "showarrow": False,
                "xanchor": "center",
                "yanchor": "bottom",
                "yshift": 8,
                "font": {"size": 22},
            }
        )
    return annotations


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
        height=440,
        margin=dict(l=8, r=8, t=36, b=80),
        xaxis_title="City",
        yaxis_title=value_col,
        xaxis=dict(tickangle=-35, categoryorder="array", categoryarray=cities),
        yaxis=dict(rangemode="tozero"),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=_bar_top_icons(cities, values, surging_cities),
    )
    st.plotly_chart(fig, use_container_width=True)
