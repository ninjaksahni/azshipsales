from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.coverage import coverage_calendar_html, coverage_summary_text
from src.parser import parse_shipment_csv
from src.store import DEFAULT_DATA_PATH, ingest_rows, load_store, reset_store, save_store

st.set_page_config(page_title="Amazon Shipment Analytics", layout="wide")
st.title("Amazon shipment analytics")
st.caption("Upload last-30-days shipment CSVs; aggregates SKU sales by city and state.")

DATA_PATH = DEFAULT_DATA_PATH


def load_or_init() -> dict:
    return load_store(DATA_PATH)


def sku_overview_df(store: dict) -> pd.DataFrame:
    rows = []
    for sku, data in store.get("skus", {}).items():
        top_city = data.get("top_city") or {}
        top_state = data.get("top_state") or {}
        rows.append(
            {
                "SKU": sku,
                "Total units": int(data.get("total_quantity", 0)),
                "Total revenue (INR)": float(data.get("total_revenue_inr", 0)),
                "Top city": top_city.get("name", "—"),
                "Top city units": top_city.get("quantity", 0),
                "Top city revenue (INR)": top_city.get("revenue_inr", 0),
                "Top state": top_state.get("name", "—"),
                "Top state units": top_state.get("quantity", 0),
                "Top state revenue (INR)": top_state.get("revenue_inr", 0),
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "SKU",
                "Total units",
                "Total revenue (INR)",
                "Top city",
                "Top city units",
                "Top city revenue (INR)",
                "Top state",
                "Top state units",
                "Top state revenue (INR)",
            ]
        )
    df = pd.DataFrame(rows)
    return df.sort_values("Total units", ascending=False).reset_index(drop=True)


def bucket_to_df(buckets: dict, name_col: str) -> pd.DataFrame:
    rows = [
        {
            name_col: name,
            "Units": int(v.get("quantity", 0)),
            "Revenue (INR)": float(v.get("revenue_inr", 0)),
        }
        for name, v in buckets.items()
    ]
    if not rows:
        return pd.DataFrame(columns=[name_col, "Units", "Revenue (INR)"])
    return (
        pd.DataFrame(rows)
        .sort_values("Units", ascending=False)
        .reset_index(drop=True)
    )


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

total_units = sum(int(s.get("total_quantity", 0)) for s in skus.values())
total_revenue = sum(float(s.get("total_revenue_inr", 0)) for s in skus.values())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total units", f"{total_units:,}")
c2.metric("Total revenue (INR)", f"{total_revenue:,.2f}")
c3.metric("SKUs", len(skus))
c4.metric("Uploads", len(store.get("uploads", [])))

st.subheader("SKU overview")
st.dataframe(sku_overview_df(store), use_container_width=True, hide_index=True)

if skus:
    st.subheader("SKU detail")
    sku_choice = st.selectbox("Select SKU", sorted(skus.keys()))
    rec = skus[sku_choice]
    top_city = rec.get("top_city")
    top_state = rec.get("top_state")
    if top_city:
        st.info(
            f"**{sku_choice}** sells most to **{top_city['name']}** "
            f"({top_city['quantity']} units, ₹{top_city['revenue_inr']:,.2f} revenue)."
        )
    if top_state:
        st.write(
            f"Top state: **{top_state['name']}** "
            f"({top_state['quantity']} units, ₹{top_state['revenue_inr']:,.2f})."
        )

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**By city**")
        city_df = bucket_to_df(rec.get("cities", {}), "City")
        st.dataframe(city_df, use_container_width=True, hide_index=True)
        if not city_df.empty:
            st.bar_chart(city_df.set_index("City")["Units"])
    with col_b:
        st.markdown("**By state**")
        state_df = bucket_to_df(rec.get("states", {}), "State")
        st.dataframe(state_df, use_container_width=True, hide_index=True)
        if not state_df.empty:
            st.bar_chart(state_df.set_index("State")["Units"])

if store.get("uploads"):
    with st.expander("Upload history"):
        st.dataframe(pd.DataFrame(store["uploads"]), use_container_width=True, hide_index=True)

if DATA_PATH.exists():
    st.download_button(
        "Download aggregates.json",
        data=json.dumps(store, indent=2, ensure_ascii=False),
        file_name="aggregates.json",
        mime="application/json",
    )
