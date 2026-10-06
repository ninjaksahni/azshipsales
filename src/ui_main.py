from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.constants import (
    METRIC_OPTIONS,
    METRIC_UNITS_LABEL,
    SESSION_CITY,
    SESSION_METRIC,
    SESSION_SKUS,
)
from src.fulfillment import (
    Metric,
    build_city_index,
    chart_series_from_table,
    cities_sorted,
    default_city,
    filter_cities,
    format_hero_city_to_sku,
    format_hero_sku_to_city,
    format_sku_selection_label,
    merge_sku_records,
    places_table_df,
    ranked_places_for_sku,
    ranked_skus_for_city,
    sku_glance_dataframe,
    skus_sorted,
    store_summary,
)
from src.session_prefs import get_metric
from src.sku_selection import ensure_default_skus, selected_skus
from src.store_cache import store_to_json_bytes
from src.ui_maps import render_maps_tab
from src.ui_momentum import render_market_momentum


def _metric_column_config(metric: Metric) -> dict[str, Any]:
    if metric == "units":
        return {
            "Total units": st.column_config.NumberColumn(format="%d"),
            "Units": st.column_config.NumberColumn(format="%d"),
            "Top market (units)": st.column_config.NumberColumn(format="%d"),
        }
    return {
        "Revenue (₹)": st.column_config.NumberColumn(format="₹%.2f"),
        "Top market (₹)": st.column_config.NumberColumn(format="₹%.2f"),
    }


def render_summary_strip(skus: dict[str, Any]) -> None:
    summary = store_summary(skus)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Products (SKUs)", summary["sku_count"])
    c2.metric("Cities with demand", summary["city_count"])
    c3.metric("Units shipped", f"{int(summary['total_units']):,}")
    c4.metric("Revenue (INR)", f"₹{summary['total_revenue_inr']:,.2f}")


def render_main(store: dict[str, Any], data_path: Path) -> None:
    skus = store.get("skus", {})
    if not skus:
        st.info(
            "No shipment data yet. Upload **Shipment Sales** CSV reports from the sidebar."
        )
        return

    if SESSION_METRIC not in st.session_state:
        st.session_state[SESSION_METRIC] = METRIC_UNITS_LABEL

    render_summary_strip(skus)

    st.radio(
        "Rank by",
        options=METRIC_OPTIONS,
        horizontal=True,
        key=SESSION_METRIC,
        help="Units = best for fulfillment planning. Revenue = product amount in INR.",
    )
    metric: Metric = get_metric()
    ensure_default_skus(skus, metric)

    tab_sku, tab_city, tab_maps = st.tabs(
        ["SKU → markets", "City → assortment", "Maps"]
    )

    with tab_sku:
        _render_sku_tab(skus, metric, store)

    with tab_city:
        _render_city_tab(skus, metric)

    with tab_maps:
        render_maps_tab(skus, metric)

    with st.expander("Settings & export"):
        _render_settings(store, data_path)


def _render_sku_tab(skus: dict[str, Any], metric: Metric, store: dict[str, Any]) -> None:
    st.markdown("##### At a glance — where to send each product")
    glance = sku_glance_dataframe(skus, metric)
    st.dataframe(
        glance,
        use_container_width=True,
        hide_index=True,
        column_config=_metric_column_config(metric),
    )

    sku_list = ensure_default_skus(skus, metric)

    st.markdown("##### Choose SKU")
    st.caption("Click to select or deselect. Charts combine all selected products.")
    st.pills(
        "Product (SKU)",
        options=sku_list,
        selection_mode="multi",
        key=SESSION_SKUS,
        label_visibility="collapsed",
    )
    sku_choices = selected_skus(skus, metric)
    sku_label = format_sku_selection_label(sku_choices)

    rec = merge_sku_records(skus, sku_choices)
    ranked_cities = ranked_places_for_sku(rec, "cities", metric)

    st.markdown("##### Fulfillment priority")
    if ranked_cities:
        top = ranked_cities[0]
        st.success(
            format_hero_sku_to_city(
                sku_label,
                top["name"],
                top["value"],
                top["share_pct"],
                metric,
            )
        )
    else:
        st.warning(f"No city data for **{sku_label}** yet.")

    st.markdown("##### Priority markets for selected SKU(s)")
    city_df = places_table_df(
        ranked_places_for_sku(rec, "cities", metric, limit=10),
        metric,
        "City",
    )
    chart_col, table_col = st.columns([1, 1], gap="medium")
    with table_col:
        st.dataframe(
            city_df,
            use_container_width=True,
            hide_index=True,
            column_config=_metric_column_config(metric),
        )
    with chart_col:
        series = chart_series_from_table(city_df, "City", metric)
        if not series.empty:
            st.bar_chart(series, horizontal=True)
        else:
            st.caption("No chart data.")

    priority_cities = city_df["City"].tolist() if not city_df.empty else []
    render_market_momentum(sku_label, rec, store, priority_cities)

    with st.expander("By state (secondary)"):
        state_ranked = ranked_places_for_sku(rec, "states", metric, limit=10)
        st.dataframe(
            places_table_df(state_ranked, metric, "State"),
            use_container_width=True,
            hide_index=True,
            column_config=_metric_column_config(metric),
        )


def _render_city_tab(skus: dict[str, Any], metric: Metric) -> None:
    city_index = build_city_index(skus)
    cities = cities_sorted(city_index, metric)
    fallback = default_city(city_index, metric) or cities[0]

    search = st.text_input(
        "Search city",
        placeholder="Type to filter cities…",
        label_visibility="collapsed",
    )
    filtered = filter_cities(cities, search)
    if not filtered:
        st.warning("No cities match your search.")
        return

    if SESSION_CITY not in st.session_state or st.session_state[SESSION_CITY] not in filtered:
        st.session_state[SESSION_CITY] = (
            fallback if fallback in filtered else filtered[0]
        )

    col_pick, col_detail = st.columns([1, 2], gap="large")
    with col_pick:
        st.markdown("##### Choose city")
        city_choice = st.selectbox(
            "City",
            filtered,
            key=SESSION_CITY,
            label_visibility="collapsed",
        )

    ranked_skus = ranked_skus_for_city(city_index, city_choice, metric)
    with col_detail:
        st.markdown("##### Assortment priority")
        if ranked_skus:
            top = ranked_skus[0]
            st.success(
                format_hero_city_to_sku(
                    city_choice,
                    top["name"],
                    top["value"],
                    top["share_pct"],
                    metric,
                )
            )
        else:
            st.warning(f"No SKU data for **{city_choice}** yet.")

    st.markdown("##### What to stock in this city")
    sku_rank_df = places_table_df(
        ranked_skus_for_city(city_index, city_choice, metric, limit=10),
        metric,
        "SKU",
    )
    chart_col, table_col = st.columns([1, 1], gap="medium")
    with table_col:
        st.dataframe(
            sku_rank_df,
            use_container_width=True,
            hide_index=True,
            column_config=_metric_column_config(metric),
        )
    with chart_col:
        series = chart_series_from_table(sku_rank_df, "SKU", metric)
        if not series.empty:
            st.bar_chart(series, horizontal=True)


def _render_settings(store: dict[str, Any], data_path: Path) -> None:
    if store.get("uploads"):
        st.markdown("**Upload history**")
        st.dataframe(
            pd.DataFrame(store["uploads"]),
            use_container_width=True,
            hide_index=True,
        )

    st.download_button(
        "Download aggregates.json",
        data=store_to_json_bytes(store),
        file_name="aggregates.json",
        mime="application/json",
    )

    glance = sku_glance_dataframe(store.get("skus", {}), "units")
    if not glance.empty:
        st.download_button(
            "Download SKU summary (CSV)",
            data=glance.to_csv(index=False).encode("utf-8"),
            file_name="sku_fulfillment_summary.csv",
            mime="text/csv",
        )
