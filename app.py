from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.constants import (
    SESSION_CONFIRM_RESET,
    SHIPMENT_REPORT_URL,
)
from src.coverage import coverage_calendar_html, coverage_summary_text
from src.store import DEFAULT_DATA_PATH, reset_store
from src.store_cache import load_store_snapshot, store_mtime_ns
from src.ui_main import render_main
from src.upload_handler import (
    clear_upload_session_keys,
    format_cached_upload_notice,
    handle_csv_upload,
)

st.set_page_config(
    page_title="Fulfillment by city & SKU",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Where to fulfill")
st.caption(
    "See which city sells each SKU most — and what to stock in each city. "
    "Upload reports from the sidebar."
)

DATA_PATH = DEFAULT_DATA_PATH


@st.cache_data(show_spinner=False)
def _cached_store(path_str: str, mtime_ns: int) -> dict:
    return load_store_snapshot(Path(path_str))


def _get_store() -> dict:
    mtime = store_mtime_ns(DATA_PATH)
    return _cached_store(str(DATA_PATH), mtime)


def _invalidate_store_cache() -> None:
    _cached_store.clear()


def render_sidebar() -> None:
    store = _get_store()

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

    uploaded = st.file_uploader(
        "Amazon shipment report",
        type=["csv"],
        key="shipment_csv_uploader",
    )
    if uploaded is not None:
        outcome = handle_csv_upload(uploaded, DATA_PATH)
        if outcome is None:
            st.caption(format_cached_upload_notice())
        elif outcome.level == "error":
            st.error(outcome.message)
            _invalidate_store_cache()
        elif outcome.level == "warning":
            st.warning(outcome.message)
            _invalidate_store_cache()
        else:
            st.success(outcome.message)
            _invalidate_store_cache()
        store = _get_store()

    st.divider()
    st.subheader("Sales coverage")
    sales_by_day = store.get("sales_by_day", {})
    st.markdown(coverage_summary_text(sales_by_day))
    calendar_html = coverage_calendar_html(sales_by_day)
    if calendar_html:
        st.markdown(calendar_html, unsafe_allow_html=True)
    elif store.get("uploads"):
        st.caption(
            "Upload a shipment CSV again to fill the calendar. "
            "SKU totals stay deduplicated; only missing dates are added."
        )
    else:
        st.caption("Days with sales appear highlighted once you upload data.")

    st.divider()
    st.header("Data")
    if st.button("Reset all stored data", type="secondary"):
        st.session_state[SESSION_CONFIRM_RESET] = True

    if st.session_state.get(SESSION_CONFIRM_RESET):
        st.warning("This deletes all aggregates and upload history.")
        if st.button("Confirm reset", type="primary"):
            reset_store(DATA_PATH)
            clear_upload_session_keys()
            _invalidate_store_cache()
            st.session_state.pop(SESSION_CONFIRM_RESET, None)
            st.success("Data cleared.")
            st.rerun()


with st.sidebar:
    render_sidebar()

render_main(_get_store(), DATA_PATH)
