from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

import streamlit as st

from src.aggregate import recompute_sku_tops
from src.constants import SESSION_SELECTED_MONTHS
from src.coverage import _parse_day, shipment_calendar_styles_html, single_month_calendar_html


def month_keys_from_store(store: dict[str, Any]) -> list[str]:
    keys: set[str] = set()
    for day_str in store.get("sales_by_day", {}) or {}:
        d = _parse_day(day_str)
        if d:
            keys.add(f"{d.year:04d}-{d.month:02d}")
    return sorted(keys)


def format_month_key(month_key: str) -> str:
    year_s, month_s = month_key.split("-", 1)
    return datetime(int(year_s), int(month_s), 1).strftime("%B %Y")


def _month_key_for_day(day_str: str) -> str | None:
    d = _parse_day(day_str)
    if not d:
        return None
    return f"{d.year:04d}-{d.month:02d}"


def day_in_months(day_str: str, months: set[str]) -> bool:
    key = _month_key_for_day(day_str)
    return key is not None and key in months


def get_selected_months(store: dict[str, Any]) -> list[str]:
    available = month_keys_from_store(store)
    if not available:
        return []
    raw = st.session_state.get(SESSION_SELECTED_MONTHS)
    if not isinstance(raw, list) or not raw:
        return available
    valid = [m for m in raw if m in available]
    return valid if valid else available


def apply_month_filter(store: dict[str, Any], selected_months: list[str]) -> dict[str, Any]:
    available = month_keys_from_store(store)
    if not available or not selected_months:
        return store
    selected_set = set(selected_months)
    if selected_set >= set(available):
        return store

    filtered_skus: dict[str, Any] = {}
    for sku, data in store.get("skus", {}).items():
        sku_filtered = _filter_sku_record(data, selected_set)
        if sku_filtered["total_quantity"] > 0 or sku_filtered["total_revenue_inr"] > 0:
            filtered_skus[sku] = sku_filtered

    sales_by_day = store.get("sales_by_day", {}) or {}
    filtered_days = {
        day: count for day, count in sales_by_day.items() if day_in_months(day, selected_set)
    }

    out = deepcopy(store)
    out["skus"] = filtered_skus
    out["sales_by_day"] = filtered_days
    return out


def _filter_bucket(bucket: dict[str, Any], months: set[str]) -> dict[str, Any] | None:
    by_day = bucket.get("by_day") if isinstance(bucket.get("by_day"), dict) else {}
    total_qty = int(bucket.get("quantity", 0))
    total_rev = float(bucket.get("revenue_inr", 0.0))

    if by_day:
        filtered_qty = sum(
            int(by_day.get(day, 0)) for day in by_day if day_in_months(day, months)
        )
        filtered_by_day = {
            day: int(by_day[day]) for day in by_day if day_in_months(day, months)
        }
    else:
        return None

    if filtered_qty <= 0:
        return None

    filtered_rev = total_rev * (filtered_qty / total_qty) if total_qty > 0 else 0.0
    return {
        "quantity": filtered_qty,
        "revenue_inr": round(filtered_rev, 2),
        "by_day": filtered_by_day,
        "state": str(bucket.get("state") or ""),
    }


def _filter_sku_record(sku_data: dict[str, Any], months: set[str]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "total_quantity": 0,
        "total_revenue_inr": 0.0,
        "cities": {},
        "states": {},
    }
    for city, bucket in sku_data.get("cities", {}).items():
        filtered = _filter_bucket(bucket, months)
        if not filtered:
            continue
        out["cities"][city] = filtered
        out["total_quantity"] += filtered["quantity"]
        out["total_revenue_inr"] += filtered["revenue_inr"]

        state = filtered.get("state") or "UNKNOWN"
        if state not in out["states"]:
            out["states"][state] = {"quantity": 0, "revenue_inr": 0.0, "by_day": {}}
        st_bucket = out["states"][state]
        st_bucket["quantity"] = int(st_bucket["quantity"]) + filtered["quantity"]
        st_bucket["revenue_inr"] = round(
            float(st_bucket["revenue_inr"]) + filtered["revenue_inr"], 2
        )

    out["total_revenue_inr"] = round(float(out["total_revenue_inr"]), 2)
    recompute_sku_tops(out)
    return out


def _set_month_selection(months: list[str], selected: list[str]) -> None:
    """Update session selection and checkbox widget state (widgets own their keys)."""
    st.session_state[SESSION_SELECTED_MONTHS] = selected
    selected_set = set(selected)
    for month_key in months:
        st.session_state[f"month_filter_{month_key}"] = month_key in selected_set


def render_month_filter_sidebar(store: dict[str, Any]) -> None:
    months = month_keys_from_store(store)
    if not months:
        return

    st.divider()
    st.subheader("Months in view")
    st.caption("Charts and tables use only checked months. Default: all recorded months.")

    selected = set(get_selected_months(store))
    sales_by_day = store.get("sales_by_day", {}) or {}
    max_count = max(sales_by_day.values()) if sales_by_day else 1

    col_a, col_b = st.columns(2)
    if col_a.button("Select all months", use_container_width=True):
        _set_month_selection(months, months)
        st.rerun()
    if col_b.button("This month only", use_container_width=True):
        _set_month_selection(months, [months[-1]])
        st.rerun()

    st.markdown(shipment_calendar_styles_html(), unsafe_allow_html=True)

    new_selected: list[str] = []
    for month_key in months:
        year_s, month_s = month_key.split("-", 1)
        year, month = int(year_s), int(month_s)
        label = format_month_key(month_key)
        checked = st.checkbox(
            label,
            value=month_key in selected,
            key=f"month_filter_{month_key}",
        )
        if checked:
            new_selected.append(month_key)
        cal_html = single_month_calendar_html(
            year, month, sales_by_day, max_count, hide_title=True
        )
        st.markdown(
            f'<div class="cov-wrap" style="margin: -6px 0 12px 0;">{cal_html}</div>',
            unsafe_allow_html=True,
        )

    if not new_selected:
        new_selected = months
    st.session_state[SESSION_SELECTED_MONTHS] = new_selected
