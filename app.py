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
from src.paths import GEOCODE_CACHE_PATH
from src.store_sync import (
    hydrate_all_app_data,
    is_streamlit_cloud,
    last_sync_error,
    remote_store_enabled,
)
from src.ui_main import render_main
from src.upload_handler import (
    clear_upload_session_keys,
    handle_csv_uploads,
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


def _ensure_remote_hydrated() -> None:
    if st.session_state.get("_store_remote_hydrated"):
        return
    if hydrate_all_app_data(DATA_PATH, GEOCODE_CACHE_PATH):
        _invalidate_store_cache()
    st.session_state["_store_remote_hydrated"] = True


def _get_store() -> dict:
    _ensure_remote_hydrated()
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
3. Upload one or more `.csv` files below.

Re-uploading newer exports is fine — overlapping orders are deduplicated automatically.
            """.strip()
        )

    uploaded = st.file_uploader(
        "Amazon shipment reports",
        type=["csv"],
        accept_multiple_files=True,
        key="shipment_csv_uploader",
    )
    if uploaded:
        results, store_changed = handle_csv_uploads(uploaded, DATA_PATH)
        if store_changed:
            _invalidate_store_cache()

        imported_total = sum(
            o.stats.get("rows_imported", 0)
            for _, o in results
            if o and o.stats
        )
        if len(uploaded) > 1 and imported_total > 0:
            st.success(f"Finished {len(uploaded)} files — **{imported_total}** new rows imported in total.")

        for filename, outcome in results:
            if outcome is None:
                st.caption(f"**{filename}** — already processed this session.")
            elif outcome.level == "error":
                st.error(f"**{filename}** — {outcome.message}")
            elif outcome.level == "warning":
                st.warning(f"**{filename}** — {outcome.message}")
            else:
                st.success(f"**{filename}** — {outcome.message}")

        store = _get_store()

    st.divider()
    st.subheader("Shipment coverage")
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
        st.caption("Days with shipments appear highlighted once you upload data.")

    st.divider()
    st.header("Data")
    if remote_store_enabled():
        st.caption(
            "Aggregates and map geocodes sync to GitHub automatically (survives Cloud redeploys)."
        )
    elif is_streamlit_cloud():
        st.warning(
            "Add **github_store** in the app’s Streamlit **Secrets** so uploads persist after "
            "redeploy. See `.streamlit/secrets.toml.example` in the repo."
        )
    sync_err = last_sync_error()
    if sync_err:
        st.error(f"Could not sync aggregates: {sync_err}")

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
