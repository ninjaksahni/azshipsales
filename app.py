from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.coverage import coverage_calendar_html, coverage_summary_text
from src.fulfillment import (
    Metric,
    build_city_index,
    default_city,
    default_sku,
    format_hero_city_to_sku,
    format_hero_sku_to_city,
    places_table_df,
    ranked_places_for_sku,
    ranked_skus_for_city,
    sku_glance_dataframe,
)
from src.parser import parse_shipment_csv
from src.store import DEFAULT_DATA_PATH, ingest_rows, load_store, reset_store, save_store

st.set_page_config(page_title="Fulfillment by city & SKU", layout="wide")
st.title("Where to fulfill")
st.caption(
    "See which city sells each SKU most — and what to stock in each city. "
    "Upload reports from the sidebar."
)

DATA_PATH = DEFAULT_DATA_PATH


def load_or_init() -> dict:
    return load_store(DATA_PATH)


SHIPMENT_REPORT_URL = (
    "https://sellercentral.amazon.in/reportcentral/SHIPMENT_SALES/1"
)

sidebar_store = load_or_init()

with st.sidebar:
    st.header("Upload CSV")
    with st.expander("Where to download the file", expanded=False):
        st.markdown(
            f"""
1. Open the **Shipment Sales** report:  
   [Report Central → Shipment Sales]({SHIPMENT_REPORT_URL})
2. Download the report as **CSV** (last 30 days shipment data).
3. Upload that `.csv` file below.

Re-uploading newer exports is fine — overlapping orders are deduplicated automatically.
            """.strip()
        )
    uploaded = st.file_uploader("Amazon shipment report", type=["csv"])
    if uploaded is not None:
        store = load_or_init()
        try:
            parsed = parse_shipment_csv(uploaded.getvalue())
            stats = ingest_rows(
                store,
                parsed.rows,
                uploaded.name,
                parsed.rows_read,
                parsed.rows_skipped_zero_amount,
            )
            save_store(store, DATA_PATH)
            backfill = stats.get("coverage_days_backfilled", 0)
            msg = (
                f"Imported {stats['rows_imported']} rows · "
                f"Skipped {stats['rows_skipped_duplicate']} duplicates · "
                f"Skipped {stats['rows_skipped_zero_amount']} zero-amount/zero-qty"
            )
            if backfill:
                msg += f" · Backfilled {backfill} day entries for the calendar"
            st.success(msg)
        except ValueError as e:
            st.error(str(e))
        else:
            sidebar_store = load_or_init()

    st.divider()
    st.subheader("Sales coverage")
    sales_by_day = sidebar_store.get("sales_by_day", {})
    st.markdown(coverage_summary_text(sales_by_day))
    calendar_html = coverage_calendar_html(sales_by_day)
    if calendar_html:
        st.markdown(calendar_html, unsafe_allow_html=True)
    elif sidebar_store.get("uploads"):
        st.caption(
            "Upload a shipment CSV again to fill the calendar. "
            "SKU totals stay deduplicated; only missing dates are added."
        )
    else:
        st.caption("Days with sales appear highlighted once you upload data.")

    st.divider()
    st.header("Data")
    if st.button("Reset all stored data", type="secondary"):
        st.session_state["confirm_reset"] = True

    if st.session_state.get("confirm_reset"):
        st.warning("This deletes all aggregates and upload history.")
        if st.button("Confirm reset", type="primary"):
            reset_store(DATA_PATH)
            st.session_state.pop("confirm_reset", None)
            st.success("Data cleared.")
            st.rerun()

store = load_or_init()
skus = store.get("skus", {})

if not skus:
    st.info(
        "No shipment data yet. Use **Upload CSV** in the sidebar to add your "
        "Amazon Shipment Sales report."
    )
    st.stop()

metric_label = st.radio(
    "Rank by",
    options=["Units (for fulfillment)", "Revenue (₹)"],
    horizontal=True,
    help="Units = how many items shipped. Revenue = product amount in INR.",
)
metric: Metric = "units" if metric_label.startswith("Units") else "revenue"

tab_sku, tab_city = st.tabs(["SKU → markets", "City → assortment"])

with tab_sku:
    st.markdown("##### At a glance — where to send each product")
    glance = sku_glance_dataframe(skus, metric)
    st.dataframe(glance, use_container_width=True, hide_index=True)

    sku_list = sorted(skus.keys(), key=lambda s: -(
        skus[s]["total_quantity"] if metric == "units" else skus[s]["total_revenue_inr"]
    ))
    default = default_sku(skus, metric) or sku_list[0]

    col_pick, col_detail = st.columns([1, 2])
    with col_pick:
        st.markdown("##### Choose SKU")
        sku_choice = st.selectbox(
            "Product (SKU)",
            sku_list,
            index=sku_list.index(default) if default in sku_list else 0,
            label_visibility="collapsed",
        )

    rec = skus[sku_choice]
    ranked_cities = ranked_places_for_sku(rec, "cities", metric)

    with col_detail:
        if ranked_cities:
            top = ranked_cities[0]
            st.success(
                format_hero_sku_to_city(
                    sku_choice,
                    top["name"],
                    top["value"],
                    top["share_pct"],
                    metric,
                )
            )
        else:
            st.warning(f"No city data for **{sku_choice}** yet.")

    st.markdown("##### Priority markets for this SKU")
    top_n = ranked_places_for_sku(rec, "cities", metric, limit=10)
    city_df = places_table_df(top_n, metric, "City")
    chart_col, table_col = st.columns([1, 1])
    with table_col:
        st.dataframe(city_df, use_container_width=True, hide_index=True)
    with chart_col:
        if not city_df.empty:
            chart_label = "Units" if metric == "units" else "Revenue (₹)"
            chart_data = city_df.head(8).set_index("City")[chart_label]
            st.bar_chart(chart_data, horizontal=True)

    with st.expander("By state (secondary)"):
        state_ranked = ranked_places_for_sku(rec, "states", metric, limit=10)
        st.dataframe(
            places_table_df(state_ranked, metric, "State"),
            use_container_width=True,
            hide_index=True,
        )

with tab_city:
    city_index = build_city_index(skus)
    cities = sorted(
        city_index.keys(),
        key=lambda c: -(
            city_index[c]["quantity"]
            if metric == "units"
            else city_index[c]["revenue_inr"]
        ),
    )
    default_c = default_city(city_index, metric) or cities[0]

    col_pick, col_detail = st.columns([1, 2])
    with col_pick:
        st.markdown("##### Choose city")
        city_choice = st.selectbox(
            "City",
            cities,
            index=cities.index(default_c) if default_c in cities else 0,
            label_visibility="collapsed",
        )

    ranked_skus = ranked_skus_for_city(city_index, city_choice, metric)
    with col_detail:
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
    chart_col, table_col = st.columns([1, 1])
    with table_col:
        st.dataframe(sku_rank_df, use_container_width=True, hide_index=True)
    with chart_col:
        if not sku_rank_df.empty:
            chart_label = "Units" if metric == "units" else "Revenue (₹)"
            st.bar_chart(
                sku_rank_df.head(8).set_index("SKU")[chart_label],
                horizontal=True,
            )

with st.expander("Settings & export"):
    total_units = sum(int(s.get("total_quantity", 0)) for s in skus.values())
    total_revenue = sum(float(s.get("total_revenue_inr", 0)) for s in skus.values())
    m1, m2, m3 = st.columns(3)
    m1.metric("Total units (all SKUs)", f"{total_units:,}")
    m2.metric("Total revenue (INR)", f"{total_revenue:,.2f}")
    m3.metric("Data uploads", len(store.get("uploads", [])))

    if store.get("uploads"):
        st.markdown("**Upload history**")
        st.dataframe(pd.DataFrame(store["uploads"]), use_container_width=True, hide_index=True)

    if DATA_PATH.exists():
        st.download_button(
            "Download aggregates.json",
            data=json.dumps(store, indent=2, ensure_ascii=False),
            file_name="aggregates.json",
            mime="application/json",
        )
